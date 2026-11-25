"""Gera as áreas de demonstração e os projetos de carbono FICTÍCIOS.

As posições foram escolhidas varrendo Lábrea (AM) numa grade de 8 km e cruzando cada
célula com DETER, TIs e UCs. Os polígonos são irregulares e determinísticos (mesma
saída a cada execução).

    uv run python scripts/demo/gerar_areas.py

Saídas:
  public/demo/*.geojson                   áreas para testar na tela (upload)
  data/exemplos/projetos_carbono.geojson  "registro" fictício para a checagem de dupla contagem

Nenhum desses projetos existe. Os códigos usam o prefixo EXEMPLO- de propósito.
"""

import json
import math
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Polygon, mapping

RAIZ = Path(__file__).resolve().parents[2]
para_metros = Transformer.from_crs(4326, 5880, always_xy=True).transform
para_graus = Transformer.from_crs(5880, 4326, always_xy=True).transform

# Variação do raio em cada vértice: dá um contorno de "propriedade", não um círculo.
FORMA = (1.00, 0.86, 1.12, 0.95, 1.08, 0.82, 1.05, 0.93, 1.15, 0.88, 1.02, 0.90)


def poligono(lon: float, lat: float, raio_m: float, giro: int = 0) -> Polygon:
    cx, cy = para_metros(lon, lat)
    n = len(FORMA)
    pontos = [
        (
            cx + raio_m * FORMA[(i + giro) % n] * math.cos(2 * math.pi * i / n),
            cy + raio_m * FORMA[(i + giro) % n] * math.sin(2 * math.pi * i / n),
        )
        for i in range(n)
    ]
    # 5 casas decimais (~1 m) bastam e deixam o arquivo legível.
    return Polygon([tuple(round(v, 5) for v in para_graus(x, y)) for x, y in pontos])


def feature(geom: Polygon, **props) -> dict:
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


def salvar(caminho: Path, features: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=1
        )
    )
    print(f"  {caminho.relative_to(RAIZ)}")


AREAS_DEMO = {
    "1_area_limpa": {
        "geom": poligono(-66.680, -7.310, 4000, giro=0),
        "nome": "Área de demonstração 1: sem sinais",
        "data_inicio": "2019-01-01",
    },
    "2_desmatamento_e_dupla_contagem": {
        "geom": poligono(-65.976, -9.170, 4000, giro=3),
        "nome": "Área de demonstração 2: desmatamento após o início e sobreposição com outro projeto",
        "data_inicio": "2020-01-01",
    },
    "3_sobreposicao_uc": {
        "geom": poligono(-66.485, -9.153, 4000, giro=6),
        "nome": "Área de demonstração 3: sobreposição com Unidade de Conservação",
        "data_inicio": "2021-03-01",
    },
}

PROJETOS_FICTICIOS = [
    {
        "codigo": "EXEMPLO-001",
        "nome": "Projeto Exemplo Alfa (fictício)",
        "data_inicio": "2017-05-01",
        "geom": poligono(-66.787, -7.236, 4500, giro=2),
    },
    # ~6,5 km a leste da área de demo 2: sobreposição parcial (dupla contagem)
    {
        "codigo": "EXEMPLO-002",
        "nome": "Projeto Exemplo Beta (fictício)",
        "data_inicio": "2018-09-01",
        "geom": poligono(-65.917, -9.170, 4000, giro=7),
    },
    {
        "codigo": "EXEMPLO-003",
        "nome": "Projeto Exemplo Gama (fictício)",
        "data_inicio": "2020-02-01",
        "geom": poligono(-66.722, -9.640, 3500, giro=9),
    },
]


def main() -> None:
    print("Áreas de demo")
    for arquivo, a in AREAS_DEMO.items():
        salvar(
            RAIZ / "public" / "demo" / f"{arquivo}.geojson",
            [feature(a["geom"], nome=a["nome"], data_inicio=a["data_inicio"], ficticio=True)],
        )
    print("Projetos fictícios")
    salvar(
        RAIZ / "data" / "exemplos" / "projetos_carbono.geojson",
        [
            feature(p["geom"], codigo=p["codigo"], nome=p["nome"], data_inicio=p["data_inicio"])
            for p in PROJETOS_FICTICIOS
        ],
    )


if __name__ == "__main__":
    main()
