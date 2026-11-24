"""DETER Amazônia (INPE): alertas quase diários de desmatamento, com data."""

from _comum import DADOS, MUNICIPIO_IBGE, Fonte, carregar, recortar, regiao, wfs_terrabrasilis

# Classes do DETER que contam como perda de floresta para a checagem 1.
# Ficam de fora: CICATRIZ_DE_QUEIMADA, DEGRADACAO, CORTE_SELETIVO, CS_* (degradação).
CLASSES = ("DESMATAMENTO_CR", "DESMATAMENTO_VEG", "MINERACAO")


def main() -> None:
    print("DETER")
    reg = regiao()
    gdf = wfs_terrabrasilis(
        "deter-amz:deter_amz", DADOS / f"deter_{MUNICIPIO_IBGE}.geojson", bbox=tuple(reg.total_bounds)
    )
    gdf = recortar(gdf, reg)
    gdf = gdf[gdf["classname"].isin(CLASSES)]
    fonte = Fonte(
        id="deter",
        nome="DETER Amazônia (INPE / TerraBrasilis)",
        url="https://terrabrasilis.dpi.inpe.br/app/map/deforestation?hl=pt-br",
        licenca="CC BY-SA 4.0 (a confirmar)",
        atualizado_em=gdf["view_date"].max(),
    )
    carregar(
        gdf,
        "alertas_desmatamento",
        {"id_origem": "gid", "classe": "classname", "data_deteccao": "view_date::date"},
        fonte,
    )


if __name__ == "__main__":
    main()
