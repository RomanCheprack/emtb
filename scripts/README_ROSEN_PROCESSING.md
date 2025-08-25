# Generic Scraper Data Processing Scripts

This directory contains **generic scripts** to process **any new scraper data** and integrate it into the EMTB site. The system is designed to be scalable and handle any future scrapers you add.

## Overview

The system automatically detects new scraper files in `data/scraped_raw_data/` and processes them to:

1. **Standardize** the data format to match other scrapers
2. **Add** the standardized data to the combined bikes file
3. **Import** the data into the database

## Scripts

### 1. `process_new_scrapers.py` (Recommended - Main Script)
**Complete pipeline script** - automatically detects and processes any new scraper data.

```bash
cd scripts
python process_new_scrapers.py
```

**Features:**
- Automatically detects new scraper files
- Processes all new scrapers in one command
- Can target specific scrapers
- Flexible options for different workflows

### 2. `data/standardize_new_scrapers.py` (Standardization Only)
**Generic standardization script** - processes any new scraper data and adds it to standardized files.

```bash
cd scripts
python data/standardize_new_scrapers.py
```

**Features:**
- Automatically detects new scraper files
- Standardizes field names and data format
- Saves individual standardized files
- Updates `all_bikes_standardized.json`
- Handles duplicate detection

### 3. `db/import_standardized_data.py` (Database Import Only)
**Generic database import script** - imports any standardized scraper data to the database.

```bash
cd scripts
python db/import_standardized_data.py
```

**Features:**
- Imports all standardized scraper files
- Generates unique IDs for bikes
- Checks for existing bikes to avoid duplicates
- Handles any standardized scraper data

## Usage Examples

### Complete Process (Recommended)
```bash
# Process all new scrapers automatically
cd scripts
python process_new_scrapers.py
```

### Specific Scraper Processing
```bash
# Process a specific scraper (e.g., rosen, cobra, new_scraper)
python process_new_scrapers.py --scraper rosen
python process_new_scrapers.py -s cobra
```

### Step-by-Step Processing
```bash
# 1. Only standardize data (skip database import)
python process_new_scrapers.py --standardize-only

# 2. Only import to database (skip standardization)
python process_new_scrapers.py --import-only

# 3. Process specific scraper with specific step
python process_new_scrapers.py --scraper rosen --standardize-only
python process_new_scrapers.py --scraper rosen --import-only
```

### Individual Script Usage
```bash
# Standardize all new scrapers
python data/standardize_new_scrapers.py

# Standardize specific scraper
python data/standardize_new_scrapers.py --scraper rosen

# Import all standardized data
python db/import_standardized_data.py

# Import specific scraper
python db/import_standardized_data.py --scraper rosen
```

## How It Works

### Automatic Detection
The system automatically detects new scraper files by:
1. Scanning `data/scraped_raw_data/` for `.json` files
2. Checking which files don't have corresponding `standardized_*.json` files
3. Processing only the new files

### File Naming Convention
- **Raw data**: `data/scraped_raw_data/scraper_name.json`
- **Standardized data**: `data/standardized_data/standardized_scraper_name.json`
- **Combined data**: `data/standardized_data/all_bikes_standardized.json`

### Scalability
- **Add any new scraper** by placing its JSON file in `data/scraped_raw_data/`
- **Run the main script** to automatically process it
- **No code changes needed** for new scrapers

## Prerequisites

Before running these scripts, ensure:

1. **Scraper has been run** and generated a JSON file in `data/scraped_raw_data/`
2. **Database is initialized** (run `scripts/db/init_production_db.py` if needed)
3. **Python dependencies** are installed (requirements.txt)

## Workflow Examples

### Adding a New Scraper (e.g., "newstore")
```bash
# 1. Run your new scraper
cd data/scrapers
python newstore.py  # Creates newstore.json

# 2. Process the new data (automatically detects it)
cd ../../scripts
python process_new_scrapers.py
```

### Processing Multiple New Scrapers
```bash
# If you have multiple new scrapers (e.g., rosen.json, newstore.json, etc.)
cd scripts
python process_new_scrapers.py
# Automatically processes all new files
```

### Selective Processing
```bash
# Process only specific scrapers
python process_new_scrapers.py --scraper rosen
python process_new_scrapers.py --scraper newstore

# Process all but skip database import
python process_new_scrapers.py --standardize-only
```

## Output Files

After running the scripts, you'll have:

- `data/standardized_data/standardized_[scraper_name].json` - Individual standardized files
- `data/standardized_data/all_bikes_standardized.json` - Updated combined file
- Database entries in `emtb.db` - All bikes added to bikes table

## Error Handling

The scripts include comprehensive error handling for:
- Missing input files
- Duplicate bikes (skipped automatically)
- Database connection issues
- Data format problems
- Individual scraper failures (continues with others)

## Field Mapping

The standardization process automatically maps various field names to the standard format:
- `image_URL` → `image_url`
- `product_URL` → `product_url`
- `original_price` → `price`
- Hebrew field names → English equivalents
- And many more variations...

## Verification

After running the scripts, you can verify the data:

1. **Check standardized files**: `data/standardized_data/standardized_*.json`
2. **Check combined file**: `data/standardized_data/all_bikes_standardized.json`
3. **Check database**: Use the web application to view bikes
4. **Check counts**: The scripts report detailed statistics

## Troubleshooting

### Common Issues

1. **"No new scraper files found"**
   - Ensure your scraper has generated a JSON file in `data/scraped_raw_data/`
   - Check that the file isn't already standardized

2. **"Standardized file not found"**
   - Run the standardization script first: `python data/standardize_new_scrapers.py`

3. **Database errors**
   - Ensure database is initialized: `python db/init_production_db.py`
   - Check database permissions and path

4. **Import errors**
   - Ensure all dependencies are installed
   - Check Python path and script locations

### Debug Mode

For detailed debugging, you can run individual scripts and check the console output for specific error messages.

## Data Quality Features

The scripts include comprehensive data cleaning:
- Removes problematic characters
- Handles missing fields gracefully
- Validates data types
- Generates unique IDs
- Prevents duplicate entries
- Preserves Hebrew text while standardizing field names

## Future-Proof Design

This system is designed to be:
- **Scalable**: Add unlimited new scrapers
- **Maintainable**: No code changes needed for new scrapers
- **Flexible**: Multiple processing options
- **Robust**: Comprehensive error handling
- **Consistent**: Follows existing project patterns

## Notes

- The scripts follow the same patterns as existing scrapers
- All field names are converted to lowercase (following project conventions)
- Hebrew text is preserved but field names are translated to English
- Gallery images are stored as JSON arrays in the database
- The `source_file` field tracks which scraper generated each bike
- The system automatically handles any new scraper without code modifications
