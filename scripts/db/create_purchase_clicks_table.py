#!/usr/bin/env python3
"""
Create the purchase_clicks table once (idempotent: safe if the table already exists).

Run from project root with your venv activated and DATABASE_URL / .env pointing at MySQL:

    python scripts/db/create_purchase_clicks_table.py
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from dotenv import load_dotenv  # noqa: E402
from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.models import PurchaseClick  # noqa: E402


def main():
    load_dotenv(override=True)
    app = create_app()
    with app.app_context():
        PurchaseClick.__table__.create(db.engine, checkfirst=True)
        print("Done: table purchase_clicks exists (created if it was missing).")


if __name__ == "__main__":
    main()
