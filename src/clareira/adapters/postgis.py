"""Adaptador PostGIS: implementa as portas com consultas SQL.

Regras geográficas usadas em todas as consultas:
  1. Interseção em EPSG:4326 (onde as geometrias são válidas); só o RESULTADO é
     reprojetado para EPSG:5880 para medir a área. Reprojetar antes pode criar
     autointerseções e quebrar o ST_Intersection.
  2. A área total é medida sobre a UNIÃO das interseções: DETER e PRODES (ou uma TI
     e uma UC) costumam cobrir o mesmo chão, e cada hectare só pode contar uma vez.
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import Engine, create_engine, text

from clareira.domain.modelos import Analise, Fonte, Item, Sobreposicao
from clareira.serializacao import de_dict, para_dict

ENTRADA = "ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)"
HA = "ST_Area(ST_Transform({}, 5880)) / 10000.0"
# ~10 m de tolerância: o desenho no mapa fica leve sem mudar a leitura visual.
SIMPLIFICAR = 0.0001
ITEM_MINIMO_HA = 0.01


def _sql_sobreposicao(pedacos: str) -> str:
    """`pedacos` é um SELECT que devolve (rotulo text, gi geometry) para a área :g."""
    return f"""
    WITH p AS (SELECT {ENTRADA} AS g),
    x AS ({pedacos}),
    u AS (SELECT ST_Union(gi) AS g FROM x)
    SELECT
        coalesce({HA.format("u.g")}, 0) AS ha,
        ST_AsGeoJSON(ST_SimplifyPreserveTopology(u.g, {SIMPLIFICAR}), 6) AS geometria,
        (SELECT coalesce(json_agg(json_build_object('rotulo', rotulo, 'ha', ha)
                                  ORDER BY ordem, ha DESC), '[]'::json)
           FROM (SELECT rotulo, min(ordem) AS ordem, {HA.format("ST_Union(gi)")} AS ha
                   FROM x GROUP BY rotulo) i
          WHERE ha >= {ITEM_MINIMO_HA}) AS itens
    FROM u
    """


SQL_DESMATAMENTO = _sql_sobreposicao(
    """
    SELECT extract(year FROM a.data_deteccao)::int::text AS rotulo,
           extract(year FROM a.data_deteccao)::int AS ordem,
           ST_Intersection(a.geom, p.g) AS gi
      FROM alertas_desmatamento a, p
     WHERE ST_Intersects(a.geom, p.g) AND a.data_deteccao >= :inicio
    """
)

SQL_AREAS_PROTEGIDAS = _sql_sobreposicao(
    """
    SELECT 'Terra Indígena ' || t.nome AS rotulo, 0 AS ordem, ST_Intersection(t.geom, p.g) AS gi
      FROM terras_indigenas t, p WHERE ST_Intersects(t.geom, p.g)
    UNION ALL
    SELECT u.categoria || ': ' || u.nome, 1, ST_Intersection(u.geom, p.g)
      FROM unidades_conservacao u, p WHERE ST_Intersects(u.geom, p.g)
    """
)

SQL_OUTROS_PROJETOS = _sql_sobreposicao(
    """
    SELECT c.codigo || ' · ' || c.nome AS rotulo, 0 AS ordem, ST_Intersection(c.geom, p.g) AS gi
      FROM projetos_carbono c, p
     WHERE ST_Intersects(c.geom, p.g) AND c.codigo IS DISTINCT FROM :codigo
    """
)


class RepositorioPostgis:
    """Implementa RepositorioGeografico e RepositorioAnalises."""

    def __init__(self, engine: Engine | str):
        self.engine = (
            create_engine(engine, pool_pre_ping=True) if isinstance(engine, str) else engine
        )

    # --- RepositorioGeografico -------------------------------------------------

    def normalizar(self, geometria: dict) -> tuple[dict, float]:
        sql = f"""
        WITH p AS (SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid({ENTRADA}), 3)) AS g)
        SELECT ST_AsGeoJSON(g, 7) AS geometria, coalesce({HA.format("g")}, 0) AS ha FROM p
        """
        with self.engine.connect() as con:
            r = con.execute(text(sql), {"g": json.dumps(geometria)}).one()
        return json.loads(r.geometria), float(r.ha)

    def fracao_coberta(self, geometria: dict) -> float:
        sql = f"""
        WITH p AS (SELECT {ENTRADA} AS g),
        c AS (SELECT ST_Union(geom) AS g FROM cobertura)
        SELECT CASE WHEN c.g IS NULL THEN 0
                    ELSE {HA.format("ST_Intersection(p.g, c.g)")} / nullif({HA.format("p.g")}, 0)
               END AS fracao
          FROM p, c
        """
        with self.engine.connect() as con:
            return float(con.execute(text(sql), {"g": json.dumps(geometria)}).scalar() or 0)

    def desmatamento_desde(self, geometria: dict, inicio: date) -> Sobreposicao:
        return self._sobreposicao(SQL_DESMATAMENTO, geometria, inicio=inicio)

    def areas_protegidas(self, geometria: dict) -> Sobreposicao:
        return self._sobreposicao(SQL_AREAS_PROTEGIDAS, geometria)

    def outros_projetos(self, geometria: dict, codigo_ignorar: str | None) -> Sobreposicao:
        return self._sobreposicao(SQL_OUTROS_PROJETOS, geometria, codigo=codigo_ignorar)

    def fontes(self) -> list[Fonte]:
        sql = "SELECT id, nome, url, atualizado_em, licenca FROM fontes ORDER BY id"
        with self.engine.connect() as con:
            return [Fonte(**r._mapping) for r in con.execute(text(sql))]

    def cobertura(self) -> dict:
        sql = """
        SELECT json_build_object('type', 'FeatureCollection', 'features', coalesce(json_agg(
                 json_build_object('type', 'Feature',
                   'properties', json_build_object('id', id, 'nome', nome),
                   'geometry', ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.001), 5)::json)),
               '[]'::json))
          FROM cobertura
        """
        with self.engine.connect() as con:
            return con.execute(text(sql)).scalar()

    def _sobreposicao(self, sql: str, geometria: dict, **params) -> Sobreposicao:
        with self.engine.connect() as con:
            r = con.execute(text(sql), {"g": json.dumps(geometria), **params}).one()
        return Sobreposicao(
            ha=float(r.ha),
            geometria=json.loads(r.geometria) if r.geometria else None,
            itens=[Item(rotulo=i["rotulo"], ha=float(i["ha"])) for i in r.itens],
        )

    # --- RepositorioAnalises ---------------------------------------------------

    def salvar(self, analise: Analise) -> None:
        with self.engine.begin() as con:
            con.execute(
                text("INSERT INTO analises (id, criada_em, resultado) VALUES (:id, :c, :r)"),
                {"id": analise.id, "c": analise.criada_em, "r": json.dumps(para_dict(analise))},
            )

    def buscar(self, id_analise: str) -> Analise | None:
        with self.engine.connect() as con:
            r = con.execute(
                text("SELECT resultado FROM analises WHERE id = CAST(:id AS uuid)"),
                {"id": id_analise},
            ).scalar()
        return de_dict(r) if r else None

    def saudavel(self) -> bool:
        with self.engine.connect() as con:
            return con.execute(text("SELECT 1")).scalar() == 1
