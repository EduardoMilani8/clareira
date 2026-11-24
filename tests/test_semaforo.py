import pytest

from clareira.domain.semaforo import Nivel, classificar, percentual


def test_sem_area_afetada_e_verde():
    assert classificar(0.0, 1000.0, 1.0) is Nivel.VERDE


def test_pouca_area_afetada_e_amarelo():
    # 5 ha em 1000 ha = 0,5% (< 1%)
    assert classificar(5.0, 1000.0, 1.0) is Nivel.AMARELO


def test_no_limite_ja_e_vermelho():
    # 10 ha em 1000 ha = exatamente 1%
    assert classificar(10.0, 1000.0, 1.0) is Nivel.VERMELHO


def test_muita_area_afetada_e_vermelho():
    assert classificar(300.0, 1000.0, 5.0) is Nivel.VERMELHO


def test_lasca_de_borda_e_verde():
    # 0,003 ha em 1000 ha: ruído de digitalização, não sinal
    assert classificar(0.003, 1000.0, 1.0) is Nivel.VERDE


def test_area_pequena_em_projeto_pequeno_nao_e_ruido():
    # 0,4 ha em 100 ha = 0,4%: pequeno em ha, mas relevante em %
    assert classificar(0.4, 100.0, 1.0) is Nivel.AMARELO


def test_percentual():
    assert percentual(25.0, 1000.0) == pytest.approx(2.5)


def test_projeto_sem_area_e_erro():
    with pytest.raises(ValueError):
        percentual(1.0, 0.0)
