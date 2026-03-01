#!/usr/bin/env python3
"""
Backfill wheel_size from JSON for bikes missing it.
Fixes bikes migrated before the root-level wheel_size migration fix.
Run after migrate_to_mysql.py if brand+wheel_size filter shows no kids bikes.

Usage: python scripts/db/backfill_wheel_size.py
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models import Bike, Brand, BikeListing, BikeSpecRaw, BikeSpecStd


def _norm_key(k):
    """Normalize spec key for comparison (e.g. 'wheel size' -> 'wheel_size')"""
    return (k or '').lower().replace(' ', '_').replace('-', '_').strip()


def _get_wheel_size_value(bike_data):
    """Get canonical wheel_size value. Prefer root (int) over specs (str)."""
    root_val = bike_data.get('wheel_size')
    if root_val is not None and str(root_val).strip():
        return str(root_val).strip()
    specs = bike_data.get('specs', {})
    for k, v in specs.items():
        if _norm_key(k) == 'wheel_size' and v and str(v).strip():
            return str(v).strip()
    return None


def backfill_wheel_size():
    """Add wheel_size from JSON to bikes missing it"""
    load_dotenv(override=True)
    app = create_app()

    json_dir = Path(project_root) / "data" / "standardized_data"
    json_files = list(json_dir.glob("standardized_*.json"))

    if not json_files:
        print("❌ No standardized JSON files found")
        return

    print(f"📂 Found {len(json_files)} JSON file(s)")

    with app.app_context():
        added_raw = 0
        added_std = 0
        skipped = 0

        for json_file in json_files:
            print(f"\n📄 Processing {json_file.name}...")

            with open(json_file, 'r', encoding='utf-8') as f:
                bikes_data = json.load(f)

            for bike_data in bikes_data:
                firm = bike_data.get('firm')
                model = bike_data.get('model')
                if not firm or not model:
                    continue

                wheel_size_str = _get_wheel_size_value(bike_data)
                if not wheel_size_str:
                    continue

                # Find bike in DB
                bike = db.session.query(Bike).join(Bike.brand).filter(
                    Bike.brand.has(name=firm),
                    Bike.model == model
                ).first()

                if not bike:
                    skipped += 1
                    continue

                # Check if wheel_size already in raw_specs
                has_raw = False
                if bike.listings:
                    listing = bike.listings[0]
                    for raw in listing.raw_specs:
                        if _norm_key(raw.spec_key_raw) == 'wheel_size':
                            has_raw = True
                            break
                    if not has_raw:
                        db.session.add(BikeSpecRaw(
                            listing_id=listing.id,
                            spec_key_raw='wheel_size',
                            spec_value_raw=wheel_size_str,
                            scraped_at=datetime.now(timezone.utc)
                        ))
                        added_raw += 1
                        print(f"   ✅ Added raw wheel_size={wheel_size_str}: {firm} {model}")

                # Check if wheel_size already in BikeSpecStd
                has_std = any(s.spec_name == 'wheel_size' for s in bike.standardized_specs)
                if not has_std:
                    db.session.add(BikeSpecStd(
                        bike_id=bike.id,
                        spec_name='wheel_size',
                        spec_value=wheel_size_str,
                        updated_at=datetime.now(timezone.utc)
                    ))
                    added_std += 1

        db.session.commit()
        print(f"\n✅ Backfill complete: {added_raw} raw_specs, {added_std} std_specs added")
        if skipped:
            print(f"   (Skipped {skipped} bikes not found in DB)")


if __name__ == "__main__":
    backfill_wheel_size()
