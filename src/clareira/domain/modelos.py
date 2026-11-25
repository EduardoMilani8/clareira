"""Objetos do domínio. Sem dependência de banco nem de HTTP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from clareira.domain.semaforo import Nivel, TipoChecagem


@dataclass(frozen=True)
class Fonte:
    id: str
    nome: str
    url: str
    atualizado_em: date | None
    licenca: str | None = None


@dataclass(frozen=True)
class Item:
    """Uma parte de uma sobreposição: uma TI, uma UC, um ano de desmatamento, um projeto."""

    rotulo: str
    ha: float


@dataclass(frozen=True)
class Sobreposicao:
    """O que uma consulta geográfica devolve: área total (sem contar duas vezes) e o desenho."""

    ha: float
    geometria: dict | None  # GeoJSON, já simplificado para o mapa
    itens: list[Item] = field(default_factory=list)


@dataclass(frozen=True)
class Sinal:
    tipo: TipoChecagem
    titulo: str
    nivel: Nivel
    ha: float
    percentual: float
    geometria: dict | None
    itens: list[Item]
    fontes: list[Fonte]


@dataclass(frozen=True)
class Analise:
    id: str
    criada_em: datetime
    area_ha: float
    data_inicio: date
    codigo_projeto: str | None
    geometria: dict
    sinais: list[Sinal]
    avisos: list[str]


class EntradaInvalida(ValueError):
    """A área enviada não pode ser analisada (formato, tamanho, data ou cobertura)."""
