#!/usr/bin/env python3
"""Standalone script to create/update the Azure AI Search index.

Usage:
    python scripts/create-index.py

Requires AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_INDEX_NAME env vars.
"""

import logging
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "backend"))

from app.search_index import create_or_update_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

if __name__ == "__main__":
    create_or_update_index()
    print("Index created/updated successfully.")
