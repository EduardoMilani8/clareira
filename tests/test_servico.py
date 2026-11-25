from datetime import date, timedelta

import pytest

from clareira.domain.modelos import EntradaInvalida
from clareira.domain.semaforo import Nivel, TipoChecagem
from clareira.servico import ServicoAnalise
from tests.conftest import QUADRADO, RepoFalso


def niveis(analise):
    return {s.tipo: s.nivel for s in analise.sinais}


def test_area_sem_sinais_fica_toda_verde(repo_falso):
    a = ServicoAnalise(repo_falso, repo_falso).analisar(QUADRADO, date(2020, 1, 1))
    assert set(niveis(a).values()) == {Nivel.VERDE}
    assert len(a.sinais) == 3


def test_cada_checagem_usa_o_proprio_limite():
    # 3% de desmatamento (limite 1%) e 3% de outro projeto (limite 5%)
    repo = RepoFalso(area_ha=1000, desm=30, projetos=30)
    a = ServicoAnalise(repo, repo).analisar(QUADRADO, date(2020, 1, 1))
    assert niveis(a)[TipoChecagem.DESMATAMENTO] is Nivel.VERMELHO
    assert niveis(a)[TipoChecagem.OUTRO_PROJETO] is Nivel.AMARELO
    assert niveis(a)[TipoChecagem.AREA_PROTEGIDA] is Nivel.VERDE


def test_todo_sinal_cita_as_fontes(repo_falso):
    a = ServicoAnalise(repo_falso, repo_falso).analisar(QUADRADO, date(2020, 1, 1))
    fontes = {s.tipo: [f.id for f in s.fontes] for s in a.sinais}
    assert fontes[TipoChecagem.DESMATAMENTO] == ["deter", "prodes"]
    assert fontes[TipoChecagem.AREA_PROTEGIDA] == ["ti_inpe", "cnuc"]


def test_data_de_inicio_vai_para_a_checagem_de_desmatamento(repo_falso):
    ServicoAnalise(repo_falso, repo_falso).analisar(QUADRADO, date(2021, 3, 1))
    assert ("desm", date(2021, 3, 1)) in repo_falso.chamadas


def test_codigo_do_projeto_e_ignorado_na_dupla_contagem(repo_falso):
    ServicoAnalise(repo_falso, repo_falso).analisar(QUADRADO, date(2020, 1, 1), "  VCS-123 ")
    assert ("proj", "VCS-123") in repo_falso.chamadas


def test_analise_fica_salva_para_reabrir(repo_falso):
    s = ServicoAnalise(repo_falso, repo_falso)
    a = s.analisar(QUADRADO, date(2020, 1, 1))
    assert s.buscar(a.id) == a


def test_recusa_area_fora_da_cobertura():
    repo = RepoFalso(cobertura=0.6)
    with pytest.raises(EntradaInvalida, match="fora"):
        ServicoAnalise(repo, repo).analisar(QUADRADO, date(2020, 1, 1))


def test_recusa_area_gigante():
    repo = RepoFalso(area_ha=2_000_000)
    with pytest.raises(EntradaInvalida, match="limite"):
        ServicoAnalise(repo, repo).analisar(QUADRADO, date(2020, 1, 1))


def test_recusa_data_futura(repo_falso):
    with pytest.raises(EntradaInvalida, match="futuro"):
        ServicoAnalise(repo_falso, repo_falso).analisar(QUADRADO, date.today() + timedelta(days=1))


def test_avisa_quando_inicio_e_anterior_aos_dados(repo_falso):
    a = ServicoAnalise(repo_falso, repo_falso).analisar(QUADRADO, date(2005, 1, 1))
    assert any("2008" in aviso for aviso in a.avisos)
