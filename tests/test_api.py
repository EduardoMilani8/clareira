from fastapi.testclient import TestClient

from clareira.api import AVISO_LEGAL, criar_app
from clareira.servico import ServicoAnalise
from tests.conftest import QUADRADO, RepoFalso


def cliente(repo=None) -> TestClient:
    repo = repo or RepoFalso()
    return TestClient(criar_app(ServicoAnalise(repo, repo)))


def test_post_analise_devolve_tres_sinais_e_aviso_legal():
    r = cliente(RepoFalso(desm=50)).post(
        "/api/analises", json={"geometria": QUADRADO, "data_inicio": "2020-01-01"}
    )
    assert r.status_code == 201
    corpo = r.json()
    assert [s["nivel"] for s in corpo["sinais"]] == ["vermelho", "verde", "verde"]
    assert corpo["sinais"][0]["fontes"][0]["nome"] == "DETER"
    assert corpo["aviso_legal"] == AVISO_LEGAL


def test_get_analise_reabre_pelo_id():
    c = cliente()
    criada = c.post(
        "/api/analises", json={"geometria": QUADRADO, "data_inicio": "2020-01-01"}
    ).json()
    r = c.get(f"/api/analises/{criada['id']}")
    assert r.status_code == 200 and r.json()["id"] == criada["id"]


def test_analise_inexistente_e_404():
    assert cliente().get("/api/analises/nao-existe").status_code == 404


def test_entrada_invalida_vira_422_com_mensagem():
    r = cliente(RepoFalso(cobertura=0)).post(
        "/api/analises", json={"geometria": QUADRADO, "data_inicio": "2020-01-01"}
    )
    assert r.status_code == 422
    assert "fora" in r.json()["detail"]


def test_data_malformada_vira_422():
    r = cliente().post("/api/analises", json={"geometria": QUADRADO, "data_inicio": "ontem"})
    assert r.status_code == 422


def test_cobertura():
    r = cliente().get("/api/cobertura")
    assert r.status_code == 200 and r.json()["features"][0]["properties"]["nome"] == "Teste"


def test_fontes():
    r = cliente().get("/api/fontes")
    assert r.status_code == 200
    assert {f["id"] for f in r.json()} >= {"deter", "prodes", "cnuc"}


def test_linguagem_nunca_acusa():
    """Regra do projeto: sinais de risco, nunca 'fraude' ou 'ilegal'."""
    corpo = (
        cliente(RepoFalso(desm=500, protegidas=500, projetos=500))
        .post("/api/analises", json={"geometria": QUADRADO, "data_inicio": "2020-01-01"})
        .text.lower()
    )
    for palavra in ("fraude", "fraudulento", "ilegal", "crime"):
        assert palavra not in corpo
