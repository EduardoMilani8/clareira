"""Converte Analise <-> dict (JSON da API e coluna jsonb do banco)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime

from clareira.domain.modelos import Analise, Fonte, Item, Sinal
from clareira.domain.semaforo import Nivel, TipoChecagem

# Só estes números são arredondados; coordenadas de geometria ficam intactas.
_ARREDONDAR = {"ha": 2, "percentual": 3, "area_ha": 2}


def _json(valor, chave: str | None = None):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: _json(v, k) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_json(v) for v in valor]
    if isinstance(valor, float) and chave in _ARREDONDAR:
        return round(valor, _ARREDONDAR[chave])
    return valor


def para_dict(analise: Analise) -> dict:
    d = _json(asdict(analise))
    assert isinstance(d, dict)
    return d


def fonte_de_dict(d: dict) -> Fonte:
    atualizado = d.get("atualizado_em")
    return Fonte(
        id=d["id"],
        nome=d["nome"],
        url=d["url"],
        atualizado_em=date.fromisoformat(atualizado) if atualizado else None,
        licenca=d.get("licenca"),
    )


def de_dict(d: dict) -> Analise:
    return Analise(
        id=d["id"],
        criada_em=datetime.fromisoformat(d["criada_em"]),
        area_ha=d["area_ha"],
        data_inicio=date.fromisoformat(d["data_inicio"]),
        codigo_projeto=d.get("codigo_projeto"),
        geometria=d["geometria"],
        avisos=d.get("avisos", []),
        sinais=[
            Sinal(
                tipo=TipoChecagem(s["tipo"]),
                titulo=s["titulo"],
                nivel=Nivel(s["nivel"]),
                ha=s["ha"],
                percentual=s["percentual"],
                geometria=s.get("geometria"),
                itens=[Item(**i) for i in s.get("itens", [])],
                fontes=[fonte_de_dict(f) for f in s.get("fontes", [])],
            )
            for s in d["sinais"]
        ],
    )
