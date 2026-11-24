"""Roda todas as ingestões em sequência: uv run python scripts/ingest/todas.py"""

import deter
import prodes
import terras_indigenas
import unidades_conservacao

if __name__ == "__main__":
    for modulo in (deter, prodes, terras_indigenas, unidades_conservacao):
        modulo.main()
    print("ok")
