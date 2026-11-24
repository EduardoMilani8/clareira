"""Regras do semáforo: transformam uma área afetada em verde / amarelo / vermelho.

Este módulo não conhece banco, HTTP nem mapa: só números. Por isso dá para
testar as regras isoladamente (tests/test_semaforo.py).
"""

from __future__ import annotations

from enum import StrEnum


class Nivel(StrEnum):
    VERDE = "verde"
    AMARELO = "amarelo"
    VERMELHO = "vermelho"


class TipoChecagem(StrEnum):
    DESMATAMENTO = "desmatamento_pos_inicio"
    AREA_PROTEGIDA = "sobreposicao_ti_uc"
    OUTRO_PROJETO = "sobreposicao_outro_projeto"


# Percentual da área do projeto a partir do qual o sinal fica VERMELHO.
# Abaixo disso (e acima de zero), AMARELO.
LIMITE_VERMELHO_PCT: dict[TipoChecagem, float] = {
    TipoChecagem.DESMATAMENTO: 1.0,
    TipoChecagem.AREA_PROTEGIDA: 1.0,
    TipoChecagem.OUTRO_PROJETO: 5.0,
}


# Interseções menores que isso (em ha E em %) são tratadas como ruído de borda.
# Referência: a menor área mapeada pelo DETER é ~3 ha; pelo PRODES, 6,25 ha.
TOLERANCIA_HA = 0.5
TOLERANCIA_PCT = 0.1


def percentual(ha_afetado: float, area_projeto_ha: float) -> float:
    if area_projeto_ha <= 0:
        raise ValueError("A área do projeto precisa ser maior que zero.")
    return 100.0 * ha_afetado / area_projeto_ha


def classificar(ha_afetado: float, area_projeto_ha: float, limite_vermelho_pct: float) -> Nivel:
    """Decide o nível do sinal para uma checagem.

    Regra da especificação:
      - VERDE    se não há área afetada
      - AMARELO  se há área afetada, mas abaixo de `limite_vermelho_pct` % do projeto
      - VERMELHO se a área afetada é >= `limite_vermelho_pct` % do projeto

    "Não há área afetada" inclui o ruído de borda: bases digitalizadas em escalas
    diferentes quase nunca coincidem, e a interseção gera "lascas" minúsculas.
    Só é ruído se for pequeno nos DOIS sentidos (ha e %): assim um projeto pequeno
    não esconde um sinal real (0,4 ha em 100 ha = 0,4% continua amarelo).
    """
    pct = percentual(ha_afetado, area_projeto_ha)
    if ha_afetado < TOLERANCIA_HA and pct < TOLERANCIA_PCT:
        return Nivel.VERDE
    if pct >= limite_vermelho_pct:
        return Nivel.VERMELHO
    return Nivel.AMARELO
