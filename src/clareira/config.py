"""Configuração por variáveis de ambiente (ou arquivo .env)."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://clareira:clareira@localhost:5433/clareira"

    @property
    def url_sqlalchemy(self) -> str:
        """Neon/Vercel entregam `postgres://` ou `postgresql://`; o SQLAlchemy quer o driver."""
        url = self.database_url
        for prefixo in ("postgres://", "postgresql://"):
            if url.startswith(prefixo):
                return "postgresql+psycopg://" + url[len(prefixo) :]
        return url


def criar_engine(config: Config | None = None) -> Engine:
    config = config or Config()
    serverless = bool(os.environ.get("VERCEL"))
    return create_engine(
        config.url_sqlalchemy,
        pool_pre_ping=True,
        # Em serverless, cada instância guarda no máximo 1 conexão (o pooler do Neon
        # cuida do resto); pool_recycle evita reusar conexões de instâncias congeladas.
        pool_size=1 if serverless else 5,
        max_overflow=2 if serverless else 10,
        pool_recycle=300,
        # O pooler do Neon (PgBouncer em modo transação) não combina com prepared
        # statements automáticos do psycopg 3.
        connect_args={"prepare_threshold": None},
    )
