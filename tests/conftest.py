from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from clareira.domain.modelos import Analise, Fonte, Item, Sobreposicao

DEMO = Path(__file__).resolve().parents[1] / "data" / "demo"

QUADRADO = {  # ~1.232 ha perto do equador
    "type": "Polygon",
    "coordinates": [
        [[-66.0, -9.0], [-65.968, -9.0], [-65.968, -9.032], [-66.0, -9.032], [-66.0, -9.0]]
    ],
}


def area_demo(nome: str) -> tuple[dict, date]:
    fc = json.loads((DEMO / f"{nome}.geojson").read_text())
    return fc, date.fromisoformat(fc["features"][0]["properties"]["data_inicio"])


class RepoFalso:
    """Repositório em memória: cada teste diz o que cada checagem 'encontra'."""

    def __init__(self, area_ha=1000.0, cobertura=1.0, desm=0.0, protegidas=0.0, projetos=0.0):
        self.area_ha = area_ha
        self.cobertura = cobertura
        self.ha = {"desm": desm, "prot": protegidas, "proj": projetos}
        self.salvas: dict[str, Analise] = {}
        self.chamadas: list[tuple] = []

    def normalizar(self, geometria):
        return geometria, self.area_ha

    def fracao_coberta(self, geometria):
        return self.cobertura

    def _s(self, chave, rotulo):
        ha = self.ha[chave]
        return Sobreposicao(ha=ha, geometria=None, itens=[Item(rotulo, ha)] if ha else [])

    def desmatamento_desde(self, geometria, inicio):
        self.chamadas.append(("desm", inicio))
        return self._s("desm", "2022")

    def areas_protegidas(self, geometria):
        return self._s("prot", "Terra Indígena Exemplo")

    def outros_projetos(self, geometria, codigo_ignorar):
        self.chamadas.append(("proj", codigo_ignorar))
        return self._s("proj", "EXEMPLO-999")

    def fontes(self):
        return [
            Fonte("deter", "DETER", "https://exemplo", date(2026, 11, 5)),
            Fonte("prodes", "PRODES", "https://exemplo", date(2025, 7, 31)),
            Fonte("ti_inpe", "TIs", "https://exemplo", None),
            Fonte("cnuc", "CNUC", "https://exemplo", date(2025, 8, 1)),
            Fonte("exemplos", "Exemplos", "https://exemplo", None),
        ]

    def salvar(self, analise):
        self.salvas[analise.id] = analise

    def buscar(self, id_analise):
        return self.salvas.get(id_analise)


@pytest.fixture
def repo_falso():
    return RepoFalso()


@pytest.fixture(scope="session")
def repo_real():
    """PostGIS local com as bases carregadas; pula os testes se não estiver no ar."""
    from clareira.adapters.postgis import RepositorioPostgis
    from clareira.config import Config

    repo = RepositorioPostgis(os.environ.get("DATABASE_URL", Config().database_url))
    from sqlalchemy.exc import OperationalError

    try:
        repo.saudavel()
    except OperationalError:
        pytest.skip("PostGIS indisponível (rode: docker compose up -d && scripts/ingest/todas.py)")
    return repo
