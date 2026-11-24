"""Terras Indígenas da Amazônia Legal (camada publicada pelo INPE / TerraBrasilis).

O geoserver do FUNAI (fonte primária) responde 403 para downloads automáticos,
inclusive nos links da própria página de geoprocessamento. Não contornamos isso:
usamos a camada que o INPE publica para o PRODES. Ver README, seção Fontes.
"""

from _comum import DADOS, Fonte, carregar, recortar, regiao, wfs_terrabrasilis


def main() -> None:
    print("Terras Indígenas")
    reg = regiao()
    # Camada pequena (toda a Amazônia Legal); baixa inteira e recorta.
    gdf = wfs_terrabrasilis(
        "prodes-legal-amz:indigenous_area_legal_amazon", DADOS / "ti_amazonia_legal.geojson"
    )
    gdf = recortar(gdf, reg)
    fonte = Fonte(
        id="ti_inpe",
        nome="Terras Indígenas, Amazônia Legal (FUNAI, via INPE / TerraBrasilis)",
        url="https://terrabrasilis.dpi.inpe.br/geoserver/ows",
        licenca="a confirmar",
    )
    carregar(
        gdf,
        "terras_indigenas",
        {"codigo": "terrai_cod::text", "nome": "terrai_nom", "fase": "fase_ti"},
        fonte,
    )


if __name__ == "__main__":
    main()
