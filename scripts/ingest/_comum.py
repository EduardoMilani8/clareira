"""Utilidades compartilhadas pelos scripts de ingestão.

Todo script é idempotente: baixa o arquivo bruto uma vez (cache em data/raw),
recorta para a região de demo e substitui os registros daquela fonte no banco.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import geopandas as gpd
import httpx
from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "data" / "raw"

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://clareira:clareira@localhost:5433/clareira"
)
# Região de demo: código IBGE do município. Padrão: Lábrea (AM).
MUNICIPIO_IBGE = os.environ.get("CLAREIRA_MUNICIPIO_IBGE", "1302405")

TERRABRASILIS_WFS = "https://terrabrasilis.dpi.inpe.br/geoserver/ows"


@dataclass(frozen=True)
class Fonte:
    id: str
    nome: str
    url: str
    licenca: str | None = None
    atualizado_em: date | None = None


def engine():
    return create_engine(DATABASE_URL)


def baixar(url: str, destino: Path, params: dict | None = None, forcar: bool = False) -> Path:
    """Baixa para `destino` (com cache). Grava em .part e renomeia no fim."""
    if destino.exists() and not forcar:
        print(f"  cache: {destino.relative_to(RAIZ)}")
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(destino.suffix + ".part")
    print(f"  baixando {url} ...")
    with httpx.stream("GET", url, params=params, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        with parcial.open("wb") as f:
            for pedaco in r.iter_bytes():
                f.write(pedaco)
    parcial.rename(destino)
    return destino


def wfs_terrabrasilis(
    camada: str,
    destino: Path,
    bbox: tuple[float, float, float, float] | None = None,
    filtro_cql: str | None = None,
) -> gpd.GeoDataFrame:
    """Baixa uma camada WFS do TerraBrasilis como GeoJSON (EPSG:4326).

    bbox no formato (minx, miny, maxx, maxy) = (lon, lat, lon, lat).
    O GeoServer não aceita BBOX e CQL_FILTER juntos: use um ou outro.
    """
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": camada,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }
    if bbox is not None:
        minx, miny, maxx, maxy = bbox
        # Em WFS 2.0 com URN, a ordem dos eixos do EPSG:4326 é lat,lon.
        params["BBOX"] = f"{miny},{minx},{maxy},{maxx},urn:ogc:def:crs:EPSG::4326"
    if filtro_cql is not None:
        params["CQL_FILTER"] = filtro_cql
    baixar(TERRABRASILIS_WFS, destino, params)
    return gpd.read_file(destino).set_crs(4326, allow_override=True)


def regiao() -> gpd.GeoDataFrame:
    """Polígono do município de demo (malha municipal usada pelo PRODES)."""
    gdf = wfs_terrabrasilis(
        "prodes-legal-amz:municipalities_legal_amazon",
        DADOS / f"municipio_{MUNICIPIO_IBGE}.geojson",
        filtro_cql=f"geocodigo='{MUNICIPIO_IBGE}'",
    )
    if gdf.empty:
        raise SystemExit(f"Município {MUNICIPIO_IBGE} não encontrado na Amazônia Legal.")
    return gdf


def recortar(gdf: gpd.GeoDataFrame, reg: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Mantém as feições que tocam a região (sem cortar o polígono)."""
    gdf = gdf.to_crs(4326)
    return gdf[gdf.intersects(reg.union_all())].copy()


def carregar(gdf: gpd.GeoDataFrame, tabela: str, colunas: dict[str, str], fonte: Fonte) -> int:
    """Substitui os registros de `fonte` em `tabela`.

    `colunas` mapeia coluna_destino -> expressão SQL sobre a tabela temporária.
    A geometria é corrigida no PostGIS (ST_MakeValid) e convertida em MultiPolygon.
    """
    if gdf.geometry.name != "geom":
        gdf = gdf.rename_geometry("geom")
    stg = f"stg_{tabela}"
    geom_ok = "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))"
    destino = ", ".join([*colunas, "fonte_id", "geom"])
    origem = ", ".join([*colunas.values(), ":fonte", geom_ok])

    with engine().begin() as con:
        con.execute(
            text(
                """
                INSERT INTO fontes (id, nome, url, licenca, atualizado_em, baixado_em)
                VALUES (:id, :nome, :url, :licenca, :atualizado_em, now())
                ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, url = EXCLUDED.url,
                    licenca = EXCLUDED.licenca, atualizado_em = EXCLUDED.atualizado_em,
                    baixado_em = now()
                """
            ),
            fonte.__dict__,
        )
        gdf.to_postgis(stg, con, if_exists="replace", index=False)
        con.execute(text(f"DELETE FROM {tabela} WHERE fonte_id = :fonte"), {"fonte": fonte.id})
        resultado = con.execute(
            text(
                f"INSERT INTO {tabela} ({destino}) SELECT {origem} FROM {stg} "
                f"WHERE NOT ST_IsEmpty({geom_ok})"
            ),
            {"fonte": fonte.id},
        )
        con.execute(text(f"DROP TABLE {stg}"))
    print(f"  {tabela}: {resultado.rowcount} registros de '{fonte.id}'")
    return resultado.rowcount
