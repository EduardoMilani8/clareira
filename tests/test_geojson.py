import pytest

from clareira.domain.modelos import EntradaInvalida
from clareira.geojson import extrair_poligono
from tests.conftest import QUADRADO


def test_aceita_geometria_feature_e_colecao():
    feature = {"type": "Feature", "properties": {}, "geometry": QUADRADO}
    colecao = {"type": "FeatureCollection", "features": [feature]}
    for entrada in (QUADRADO, feature, colecao):
        assert extrair_poligono(entrada)["type"] == "Polygon"


def test_junta_varios_poligonos():
    outro = {
        "type": "Polygon",
        "coordinates": [[[-65.0, -9.0], [-64.99, -9.0], [-64.99, -9.01], [-65.0, -9.0]]],
    }
    colecao = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": g} for g in (QUADRADO, outro)],
    }
    assert extrair_poligono(colecao)["type"] == "MultiPolygon"


def test_ignora_pontos_e_recusa_se_nao_houver_poligono():
    ponto = {"type": "Point", "coordinates": [-66.0, -9.0]}
    with pytest.raises(EntradaInvalida, match="polígono"):
        extrair_poligono(ponto)


def test_corrige_poligono_em_gravata_borboleta():
    gravata = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}
    assert extrair_poligono(gravata)["type"] in {"Polygon", "MultiPolygon"}


def test_recusa_coordenadas_projetadas():
    utm = {
        "type": "Polygon",
        "coordinates": [
            [[500000, 9000000], [500100, 9000000], [500100, 8999900], [500000, 9000000]]
        ],
    }
    with pytest.raises(EntradaInvalida, match="WGS 84"):
        extrair_poligono(utm)
