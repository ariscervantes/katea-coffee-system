#!/usr/bin/env python3
"""Genera docs/openapi.json a partir del esquema OpenAPI de FastAPI."""

import json
from pathlib import Path
import sys


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from main import app  # noqa: E402


def main() -> None:
    destino = RAIZ / "docs" / "openapi.json"
    destino.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Contrato generado en {destino}")


if __name__ == "__main__":
    main()
