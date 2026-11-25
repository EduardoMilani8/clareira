"""Portas: o que o serviço precisa do mundo externo, sem dizer como é feito.

O adaptador PostGIS (clareira.adapters.postgis) implementa estas interfaces; os
testes do serviço usam implementações falsas em memória.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from clareira.domain.modelos import Analise, Fonte, Sobreposicao


class RepositorioGeografico(Protocol):
    def normalizar(self, geometria: dict) -> tuple[dict, float]:
        """Corrige a geometria (MakeValid) e devolve (GeoJSON corrigido, área em ha)."""
        ...

    def fracao_coberta(self, geometria: dict) -> float:
        """Fração (0 a 1) da área que está dentro da região com dados carregados."""
        ...

    def desmatamento_desde(self, geometria: dict, inicio: date) -> Sobreposicao: ...

    def areas_protegidas(self, geometria: dict) -> Sobreposicao: ...

    def outros_projetos(self, geometria: dict, codigo_ignorar: str | None) -> Sobreposicao: ...

    def fontes(self) -> list[Fonte]: ...

    def cobertura(self) -> dict:
        """GeoJSON (FeatureCollection) da região com dados carregados."""
        ...


class RepositorioAnalises(Protocol):
    def salvar(self, analise: Analise) -> None: ...

    def buscar(self, id_analise: str) -> Analise | None: ...
