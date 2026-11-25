"""Integração com o PostGIS real e as áreas de demo (pula se o banco não estiver no ar)."""

from datetime import date

import pytest

from clareira.domain.modelos import EntradaInvalida
from clareira.domain.semaforo import Nivel, TipoChecagem
from clareira.servico import ServicoAnalise
from tests.conftest import area_demo


def sinais(repo, nome, codigo=None):
    geometria, inicio = area_demo(nome)
    analise = ServicoAnalise(repo, repo).analisar(geometria, inicio, codigo)
    return analise, {s.tipo: s for s in analise.sinais}


def test_area_limpa_fica_toda_verde(repo_real):
    _, s = sinais(repo_real, "1_area_limpa")
    assert {x.nivel for x in s.values()} == {Nivel.VERDE}


def test_area_com_desmatamento_e_dupla_contagem(repo_real):
    _, s = sinais(repo_real, "2_desmatamento_e_dupla_contagem")
    desm = s[TipoChecagem.DESMATAMENTO]
    assert desm.nivel is Nivel.VERMELHO
    assert desm.percentual > 50
    assert desm.geometria is not None
    assert all(int(i.rotulo) >= 2020 for i in desm.itens)  # só depois do início
    proj = s[TipoChecagem.OUTRO_PROJETO]
    assert proj.nivel is Nivel.VERMELHO
    assert proj.itens[0].rotulo.startswith("EXEMPLO-002")
    assert s[TipoChecagem.AREA_PROTEGIDA].nivel is Nivel.VERDE


def test_area_com_unidade_de_conservacao(repo_real):
    _, s = sinais(repo_real, "3_sobreposicao_uc")
    uc = s[TipoChecagem.AREA_PROTEGIDA]
    assert uc.nivel is Nivel.VERMELHO
    assert "IQUIRI" in uc.itens[0].rotulo


def test_codigo_proprio_nao_conta_como_dupla_contagem(repo_real):
    _, s = sinais(repo_real, "2_desmatamento_e_dupla_contagem", codigo="EXEMPLO-002")
    assert s[TipoChecagem.OUTRO_PROJETO].nivel is Nivel.VERDE


def test_desmatamento_nao_conta_hectare_duas_vezes(repo_real):
    """DETER e PRODES se sobrepõem; o total não pode passar a área nem a soma dos anos."""
    a, s = sinais(repo_real, "2_desmatamento_e_dupla_contagem")
    desm = s[TipoChecagem.DESMATAMENTO]
    assert desm.ha <= a.area_ha
    assert desm.ha <= sum(i.ha for i in desm.itens) + 0.01


def test_data_de_inicio_mais_recente_reduz_o_desmatamento(repo_real):
    geometria, _ = area_demo("2_desmatamento_e_dupla_contagem")
    servico = ServicoAnalise(repo_real, repo_real)

    def ha(inicio):
        a = servico.analisar(geometria, inicio)
        return next(x.ha for x in a.sinais if x.tipo is TipoChecagem.DESMATAMENTO)

    assert ha(date(2023, 1, 1)) < ha(date(2020, 1, 1))


def test_recusa_area_fora_de_labrea(repo_real):
    sinop_mt = {
        "type": "Polygon",
        "coordinates": [[[-55.5, -11.8], [-55.45, -11.8], [-55.45, -11.85], [-55.5, -11.8]]],
    }
    with pytest.raises(EntradaInvalida, match="fora"):
        ServicoAnalise(repo_real, repo_real).analisar(sinop_mt, date(2020, 1, 1))


def test_analise_salva_no_banco_e_reaberta(repo_real):
    a, _ = sinais(repo_real, "3_sobreposicao_uc")
    reaberta = ServicoAnalise(repo_real, repo_real).buscar(a.id)
    assert reaberta is not None
    assert [x.nivel for x in reaberta.sinais] == [x.nivel for x in a.sinais]
