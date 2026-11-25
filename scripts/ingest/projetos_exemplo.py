"""Projetos de carbono FICTÍCIOS para a checagem de dupla contagem.

Nenhum registro público oferece download em lote dos contornos dos projetos
(Verra: KML só projeto a projeto). Para a demo, carregamos exemplos gerados por
scripts/demo/gerar_areas.py. Importar registros reais é um próximo passo.
"""

import geopandas as gpd
from _comum import RAIZ, Fonte, carregar

ARQUIVO = RAIZ / "data" / "exemplos" / "projetos_carbono.geojson"


def main() -> None:
    print("Projetos de carbono (exemplos fictícios)")
    gdf = gpd.read_file(ARQUIVO).set_crs(4326, allow_override=True)
    fonte = Fonte(
        id="exemplos",
        nome="Projetos de carbono de EXEMPLO (fictícios, criados para a demonstração)",
        url="https://github.com/EduardoMilani8/clareira/tree/main/data/exemplos",
        licenca="CC0",
    )
    carregar(
        gdf,
        "projetos_carbono",
        {
            "codigo": "codigo",
            "nome": "nome",
            "data_inicio": "data_inicio::date",
            "ficticio": "true",
        },
        fonte,
    )


if __name__ == "__main__":
    main()
