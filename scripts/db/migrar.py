"""Aplica db/init/*.sql em ordem (todos idempotentes) no banco do DATABASE_URL.

Uso com o Neon, lendo a URL de um arquivo fora do git:
    uv run --env-file .env.neon python scripts/db/migrar.py
"""

from pathlib import Path

from sqlalchemy import text

from clareira.config import criar_engine

PASTA = Path(__file__).resolve().parents[2] / "db" / "init"


def main() -> None:
    engine = criar_engine()
    for arquivo in sorted(PASTA.glob("*.sql")):
        with engine.begin() as con:
            con.execute(text(arquivo.read_text()))
        print(f"  aplicado: {arquivo.name}")
    with engine.connect() as con:
        print("  PostGIS", con.execute(text("SELECT postgis_version()")).scalar())


if __name__ == "__main__":
    main()
