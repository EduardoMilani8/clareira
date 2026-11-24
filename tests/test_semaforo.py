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


def test_percentual():
    assert percentual(25.0, 1000.0) == pytest.approx(2.5)


def test_projeto_sem_area_e_erro():
    with pytest.raises(ValueError):
        percentual(1.0, 0.0)
