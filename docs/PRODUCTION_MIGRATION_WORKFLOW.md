# Production Database Migration Workflow

**Complete workflow for rebuilding the database from scratch for production deployment.**

## Overview

This document explains the CORRECT workflow for migrating bike data from scraped JSON files to the MySQL database, including handling duplicates.

## The Problem We Fixed

### What Was Happening

1. **Scrapers collect bikes from multiple category pages** on source websites
2. **Same bike appears multiple times** with different categories:
   - Electric bikes (HYBRID models) appear in both "electric" AND "mtb" categories
   - Kids bikes appear in both "kids" AND "mtb/hardtail" categories
3. **Database has unique constraint**: `UniqueConstraint("brand_id", "model", "year")`
4. **Migration would fail silently** or keep the wrong category (first occurrence)

### Example

```
STEREO HYBRID 140 HPC PRO 625 (2024)
├─ Position 0: category="electric" ✓
├─ Position 5: category="electric" (duplicate URL)
├─ Position 15: category="mtb" (same bike, wrong category!)
└─ Position 27: category="mtb" (same bike, wrong category!)
```

Without deduplication, only the first occurrence would be migrated, which might be the wrong category.

---

## The Solution

### Deduplication Logic

**Bikes are considered duplicates if they have:**
1. Same **brand** (firm)
2. Same **model** name (including wheel size like 27.5 or 29)
3. Same **product_url** (from source website)

**Why product_url instead of year?**
- ~50% of bikes are missing year data (Giant: 100%, Rosen: 99.5%)
- product_url is unique per product on source website  
- Same URL = definitely the same bike

**Category Priority Rules:**
1. **Electric bikes** (HYBRID/E-BIKE in model): `electric` > `mtb` > `road` > `kids`
2. **Kids bikes** (specific models): `kids` > `mtb` > `road` > `electric`
3. **All other bikes**: First occurrence wins

**Why this is correct:**
- ✅ Product URL uniquely identifies the bike on source website
- ✅ Works even when year data is missing (50% of bikes)
- ✅ Wheel sizes (27.5", 29") included in model names → different bikes kept separate
- ✅ Frame sizes (S, M, L, XL) stored in specs → same bike with multiple sizes
- ✅ Keeps the most appropriate category for each bike

---

## Complete Workflow

### Prerequisites

```bash
# 1. Activate virtual environment
.\env\Scripts\activate

# 2. Ensure environment variables are set
# Check that .env file exists with database credentials
```

### Step 1: Scrape Data (if needed)

```bash
# Run scrapers to get latest data
python data/scrapers/cube_full_site.py
python data/scrapers/rosen_full_site.py
# ... etc for each scraper

# Output: data/scraped_raw_data/*.json
```

### Step 2: Standardize Data

```bash
# Standardize scraped data to common format
python scripts/data/standardize_json.py

# Or for specific scraper:
python scripts/data/standardize_new_scrapers.py cube_data

# Output: data/standardized_data/standardized_*.json
```

### Step 3: **🚨 CRITICAL - Deduplicate Data**

```bash
# This MUST be run before migration!
python scripts/data/deduplicate_standardized_data.py

# What it does:
# - Removes duplicate bikes (same brand+model+year)
# - Applies category priority rules
# - Creates .backup files before modifications
# - Shows summary of duplicates removed
```

**Example output:**
```
Found 10 files to process

✅ cobra: 59 → 51 bikes (removed 8 duplicates)
✅ cube: 39 bikes (no duplicates)
✅ giant: 89 → 76 bikes (removed 13 duplicates)
...

Total bikes before: 881
Total bikes after:  819
Duplicates removed: 62
```

### Step 4: Create Fresh Database

```bash
# Drop and recreate database schema
python scripts/db/create_mysql_schema.py --force

# This will:
# - Drop all tables
# - Recreate schema
# - Add constraints (including the unique constraint)
```

### Step 5: Migrate Data to Database

```bash
# Import deduplicated data
python scripts/db/migrate_to_mysql.py --force

# What it does:
# - Reads from data/standardized_data/standardized_*.json
# - Creates brands, sources, bikes, listings, prices, specs
# - Adds performance indexes
```

**Example output:**
```
Found 10 JSON files to process

✅ Processed standardized_cobra_data.json
✅ Processed standardized_cube_data.json
...

✅ JSON Migration Complete:
   Bikes added: 819
   Bikes skipped (duplicates): 0

📊 Database Statistics:
   Brands: 25
   Sources: 10
   Bikes: 819
   Listings: 819
   Prices: 750
```

### Step 6: Verify Migration

```bash
# Check bike counts by category
python -c "
from app import create_app
from app.models import Bike
from app.extensions import db

app = create_app()
with app.app_context():
    total = Bike.query.count()
    electric = Bike.query.filter_by(category='electric').count()
    mtb = Bike.query.filter_by(category='mtb').count()
    kids = Bike.query.filter_by(category='kids').count()
    road = Bike.query.filter_by(category='road').count()
    
    print(f'Total bikes: {total}')
    print(f'Electric: {electric}')
    print(f'MTB: {mtb}')
    print(f'Kids: {kids}')
    print(f'Road: {road}')
"
```

---

## Troubleshooting

### "IntegrityError: Duplicate entry for key 'bikes.brand_id'"

**Cause:** You didn't run the deduplication script before migration.

**Solution:**
```bash
# 1. Run deduplication
python scripts/data/deduplicate_standardized_data.py

# 2. Drop and recreate database
python scripts/db/create_mysql_schema.py --force

# 3. Re-run migration
python scripts/db/migrate_to_mysql.py --force
```

### "Wrong category for bikes"

**Example:** Electric bikes showing as MTB

**Cause:** Deduplication not applied, or category priority rules need adjustment.

**Solution:**
1. Check `scripts/data/deduplicate_standardized_data.py`
2. Verify `KIDS_BIKE_MODELS` list includes all kids bikes
3. Verify `get_category_priority()` has correct rules
4. Re-run deduplication and migration

### "Bikes missing from database"

**Possible causes:**
1. **Not in JSON files** - Check `data/standardized_data/`
2. **Filtered by deduplication** - Check `.backup` files to see what was removed
3. **Migration error** - Check migration output for errors

---

## File Structure

```
data/
├── scraped_raw_data/           # Raw scraper output
│   ├── cube_data.json
│   ├── rosen_data.json
│   └── ...
│
└── standardized_data/          # Standardized format
    ├── standardized_cube_data.json
    ├── standardized_cube_data.json.backup  # Created by deduplication
    ├── standardized_rosen_data.json
    └── ...

scripts/
├── data/
│   ├── standardize_json.py            # Standardize raw data
│   └── deduplicate_standardized_data.py  # 🚨 CRITICAL - Remove duplicates
│
└── db/
    ├── create_mysql_schema.py         # Create database schema
    └── migrate_to_mysql.py             # Import data to database
```

---

## Quick Reference - Full Workflow

```bash
# Complete production migration workflow
.\env\Scripts\activate

# 1. Scrape (if needed)
python data/scrapers/cube_full_site.py
# ... run other scrapers

# 2. Standardize
python scripts/data/standardize_json.py

# 3. 🚨 DEDUPLICATE (CRITICAL!)
python scripts/data/deduplicate_standardized_data.py

# 4. Create fresh database
python scripts/db/create_mysql_schema.py --force

# 5. Migrate data
python scripts/db/migrate_to_mysql.py --force

# 6. Verify
python -c "from app import create_app; from app.models import Bike; from app.extensions import db; app = create_app(); ctx = app.app_context(); ctx.push(); print(f'Total bikes: {Bike.query.count()}'); print(f'Electric: {Bike.query.filter_by(category=\"electric\").count()}'); ctx.pop()"
```

---

## Important Notes

1. **Always run deduplication** before migration - it's not optional!
2. **Backup files** (`.backup`) are created automatically - keep these for reference
3. **Category priority rules** can be customized in `deduplicate_standardized_data.py`
4. **Wheel sizes** (27.5, 29) are part of model names - different wheel sizes = different bikes
5. **Frame sizes** (S, M, L, XL) are in specs - same bike in different sizes = one database entry

---

## Related Files

- `app/models/models.py` - Database schema with `UniqueConstraint("brand_id", "model", "year")`
- `scripts/data/deduplicate_standardized_data.py` - Deduplication script
- `scripts/db/migrate_to_mysql.py` - Migration script
- `docs/MYSQL_MIGRATION_COMPLETE.md` - Historical migration notes

