"""PRODES Amazônia Legal (INPE): desmatamento anual mapeado (mais preciso, só com ano)."""

from _comum import DADOS, MUNICIPIO_IBGE, Fonte, carregar, recortar, regiao, wfs_terrabrasilis


def main() -> None:
    print("PRODES")
    reg = regiao()
    gdf = wfs_terrabrasilis(
        "prodes-legal-amz:yearly_deforestation",
        DADOS / f"prodes_{MUNICIPIO_IBGE}.geojson",
        bbox=tuple(reg.total_bounds),
    )
    gdf = recortar(gdf, reg)
    gdf = gdf[gdf["main_class"].str.upper() == "DESMATAMENTO"]
    fonte = Fonte(
        id="prodes",
        nome="PRODES Amazônia Legal (INPE / TerraBrasilis)",
        url="https://terrabrasilis.dpi.inpe.br/app/map/deforestation?hl=pt-br",
        licenca="CC BY-SA 4.0 (a confirmar)",
        atualizado_em=gdf["image_date"].max(),
    )
    # image_date é a data da imagem de satélite em que o desmatamento foi visto.
    carregar(
        gdf,
        "alertas_desmatamento",
        {"id_origem": "uuid", "classe": "class_name", "data_deteccao": "image_date::date"},
        fonte,
    )


if __name__ == "__main__":
    main()
