"""Unidades de Conservação: Cadastro Nacional (CNUC / MMA), shapefile oficial."""

import zipfile
from datetime import date

import geopandas as gpd
from _comum import DADOS, Fonte, baixar, carregar, recortar, regiao

URL = (
    "https://dados.mma.gov.br/dataset/44b6dc8a-dc82-4a84-8d95-1b0da7c85dac/resource/"
    "6ba9a557-87e8-4882-acb7-b3e0f0ea192d/download/shp_cnuc_2025_08.zip"
)
VERSAO = date(2025, 8, 1)  # versão do arquivo (agosto/2025)


def main() -> None:
    print("Unidades de Conservação (CNUC)")
    reg = regiao()
    arquivo = baixar(URL, DADOS / "shp_cnuc_2025_08.zip")
    pasta = DADOS / "cnuc_2025_08"
    if not pasta.exists():
        with zipfile.ZipFile(arquivo) as z:
            z.extractall(pasta)
    # O shapefile está em SIRGAS 2000 (EPSG:4674); lê só o retângulo da região.
    gdf = gpd.read_file(pasta / "cnuc_2025_08.shp", bbox=tuple(reg.total_bounds))
    gdf = recortar(gdf, reg)
    fonte = Fonte(
        id="cnuc",
        nome="Cadastro Nacional de Unidades de Conservação (CNUC / MMA)",
        url="https://dados.mma.gov.br/dataset/unidadesdeconservacao",
        licenca="a confirmar",
        atualizado_em=VERSAO,
    )
    carregar(
        gdf,
        "unidades_conservacao",
        {"codigo": "cd_cnuc", "nome": "nome_uc", "categoria": "categoria", "esfera": "esfera"},
        fonte,
    )


if __name__ == "__main__":
    main()
