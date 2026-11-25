"""Roda todas as ingestões em sequência: uv run python scripts/ingest/todas.py"""

import cobertura
import deter
import prodes
import projetos_exemplo
import terras_indigenas
import unidades_conservacao

if __name__ == "__main__":
    for modulo in (
        cobertura,
        deter,
        prodes,
        terras_indigenas,
        unidades_conservacao,
        projetos_exemplo,
    ):
        modulo.main()
    print("ok")
