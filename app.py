"""Ponto de entrada da Vercel (ela procura `app` em app.py na raiz).

Localmente, use: uv run uvicorn clareira.api:app --reload
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from clareira.api import app

__all__ = ["app"]
