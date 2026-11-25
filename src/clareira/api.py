"""API HTTP (FastAPI). Rodar: uv run uvicorn clareira.api:app --reload"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from clareira.domain.modelos import EntradaInvalida
from clareira.serializacao import para_dict
from clareira.servico import ServicoAnalise

AVISO_LEGAL = (
    "Sinais automáticos a partir de dados públicos. "
    "Não constituem conclusão sobre a regularidade do projeto."
)
RAIZ = Path(__file__).resolve().parents[2]
FRONTEND = RAIZ / "frontend"
DEMO = RAIZ / "data" / "demo"


class PedidoAnalise(BaseModel):
    geometria: dict[str, Any] = Field(
        description="GeoJSON: Geometry, Feature ou FeatureCollection com o(s) polígono(s) da área."
    )
    data_inicio: date = Field(description="Data de início do projeto (AAAA-MM-DD).")
    codigo_projeto: str | None = Field(
        default=None, max_length=100, description="Código do projeto (ignorado na dupla contagem)."
    )


def criar_app(servico: ServicoAnalise) -> FastAPI:
    app = FastAPI(
        title="Clareira",
        description="Sinais de risco de créditos de carbono a partir de dados públicos.",
        version="0.1.0",
    )
    app.state.servico = servico

    @app.exception_handler(EntradaInvalida)
    async def _entrada_invalida(_: Request, erro: EntradaInvalida) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(erro)})

    @app.post("/api/analises", status_code=201)
    def criar_analise(pedido: PedidoAnalise) -> dict:
        analise = servico.analisar(pedido.geometria, pedido.data_inicio, pedido.codigo_projeto)
        return {**para_dict(analise), "aviso_legal": AVISO_LEGAL}

    @app.get("/api/analises/{id_analise}")
    def obter_analise(id_analise: str) -> dict:
        try:
            uuid.UUID(id_analise)
        except ValueError:
            raise HTTPException(status_code=404, detail="Análise não encontrada.") from None
        analise = servico.buscar(id_analise)
        if analise is None:
            raise HTTPException(status_code=404, detail="Análise não encontrada.")
        return {**para_dict(analise), "aviso_legal": AVISO_LEGAL}

    @app.get("/api/fontes")
    def listar_fontes() -> list[dict]:
        return [
            {
                **f.__dict__,
                "atualizado_em": f.atualizado_em.isoformat() if f.atualizado_em else None,
            }
            for f in servico.fontes()
        ]

    @app.get("/api/cobertura")
    def cobertura() -> dict:
        return servico.cobertura()

    @app.get("/api/saude")
    def saude() -> dict:
        return {"ok": True}

    if DEMO.is_dir():
        app.mount("/demo", StaticFiles(directory=DEMO), name="demo")
    if FRONTEND.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")

    return app


def _app_padrao() -> FastAPI:
    from clareira.adapters.postgis import RepositorioPostgis
    from clareira.config import Config

    repo = RepositorioPostgis(Config().database_url)
    return criar_app(ServicoAnalise(repo, repo))


app = _app_padrao()
