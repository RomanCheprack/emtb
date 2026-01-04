# Troubleshooting Migration Differences Between Environments

## Problem

When running `migrate_to_mysql.py`, you see different results in development vs production:

- **Development**: 1034 bikes, 11 sources
- **Production**: 1251 bikes, 10 sources

Even though the source data in `scraped_raw_data` and `standardized_data` should be the same.

## Root Causes

### 1. Database State Differences (Most Common)

The migration script **skips bikes that already exist** in the database (by `brand+model+year` or `slug`). 

The final statistics show **ALL bikes in the database**, not just the ones added in this migration run.

**What happens:**
- If your development database already has 200 bikes from a previous run
- And you migrate 1000 bikes from JSON files
- The script will skip the 200 duplicates
- Final count = 200 (existing) + 800 (new unique bikes) = 1000 bikes
- But you expected 1000 bikes total

**Solution:**
```bash
# Drop existing bike data before migration
python scripts/db/drop_bike_data.py

# Then run migration on clean database
python scripts/db/migrate_to_mysql.py --force
```

Or use the reset script:
```bash
python scripts/db/reset_and_remigrate.py --force
```

### 2. Different Source Files

Even if you think the data is the same, check:
- Number of JSON files in `data/standardized_data/`
- File names (production might have different source files)
- File sizes or bike counts per file

**Check file counts:**
```bash
# Count files
ls data/standardized_data/standardized_*.json | wc -l

# List files
ls -la data/standardized_data/standardized_*.json
```

### 3. Data Quality Issues

Some bikes might be skipped due to validation errors:
- Missing `model` field
- Model name too long (>255 characters)
- Invalid year values
- Empty slugs
- Database errors during processing

The enhanced logging in `migrate_to_mysql.py` now shows a breakdown of skip reasons:
```
✅ JSON Migration Complete:
   Bikes added: 1000
   Bikes skipped (total): 217
   
   Skip reasons breakdown:
     - Missing Model: 5
     - Duplicate In Db: 200
     - Duplicate In File: 10
     - Errors: 2
```

### 4. Different Source Counts

The source count difference (11 vs 10) suggests:
- Development might have an extra source file
- Or production is missing a source file
- Or one environment has a source with very few bikes

## How to Diagnose

### Step 1: Check File Counts

Compare the number of standardized JSON files between environments:

```bash
# Development
cd /path/to/dev/project
python -c "import os; files = [f for f in os.listdir('data/standardized_data') if f.startswith('standardized_') and f.endswith('.json') and f != 'all_bikes_standardized.json']; print(f'Files: {len(files)}'); [print(f'  - {f}') for f in sorted(files)]"

# Production (run on production server)
# Same command
```

### Step 2: Check Database State Before Migration

**Before running migration**, check if database already has data:

```python
from app import create_app
from app.models import Bike
from app.extensions import db

app = create_app()
with app.app_context():
    existing_bikes = Bike.query.count()
    print(f"Existing bikes in database: {existing_bikes}")
```

If `existing_bikes > 0`, the migration will skip those as duplicates.

### Step 3: Run Migration with Enhanced Logging

The updated `migrate_to_mysql.py` now shows detailed skip reasons. Run it and check:

```bash
python scripts/db/migrate_to_mysql.py --force
```

Look for the "Skip reasons breakdown" section to understand what's being skipped.

### Step 4: Compare JSON File Contents

If files exist but counts differ, check bike counts per file:

```python
import json
import os

json_dir = 'data/standardized_data'
files = [f for f in os.listdir(json_dir) 
         if f.startswith('standardized_') and f.endswith('.json')
         and f != 'all_bikes_standardized.json']

for json_file in sorted(files):
    with open(os.path.join(json_dir, json_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"{json_file}: {len(data) if isinstance(data, list) else 1} bikes")
```

## Recommended Workflow

To ensure consistent results between environments:

1. **Drop existing data** before migration:
   ```bash
   python scripts/db/drop_bike_data.py
   ```

2. **Run migration** on clean database:
   ```bash
   python scripts/db/migrate_to_mysql.py --force
   ```

3. **Verify results** match expected counts from JSON files

4. **Compare skip reasons** between environments to identify data quality issues

## Example: Fresh Migration

```bash
# 1. Drop all bike data (preserves users, brands, sources structure)
python scripts/db/drop_bike_data.py

# 2. Run migration on clean database
python scripts/db/migrate_to_mysql.py --force

# 3. Check results
# The "Bikes added" count should match your JSON file totals (minus skipped duplicates within files)
# The final "Bikes" count should equal "Bikes added" if database was clean
```

## Understanding the Output

The migration script now shows:

```
✅ JSON Migration Complete:
   Bikes added: 1000          ← New bikes added in this run
   Bikes skipped (total): 217 ← Total bikes skipped
   
   Skip reasons breakdown:    ← Why bikes were skipped
     - Missing Model: 5
     - Duplicate In Db: 200   ← Already in database (most common cause)
     - Duplicate In File: 10
     - Errors: 2

📊 Database Statistics:
   Bikes: 1200                ← TOTAL bikes in database (existing + new)
```

If "Bikes" count > "Bikes added", the database had existing data before migration.
