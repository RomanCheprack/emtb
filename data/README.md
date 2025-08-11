# Data Directory Structure

This directory contains all the data-related files for the EMTB site.

## Structure

```
data/
├── scrapers/              # All scraper scripts
│   ├── motofan.py
│   ├── ofanaim.py
│   ├── motosport.py
│   └── ... (other scrapers)
├── scraped_raw_data/      # Raw scraped JSON files
│   ├── motofan.json
│   ├── ofanaim.json
│   ├── motosport.json
│   └── ... (other JSON files)
├── standardized_data/     # Standardized JSON files
│   ├── standardized_motofan.json
│   ├── standardized_ofanaim.json
│   ├── standardized_motosport.json
│   ├── all_bikes_standardized.json
│   └── ... (other standardized files)
└── README.md             # This file
```

## Workflow

The data processing follows this workflow:

1. **Scraping**: Run scrapers to collect data from websites
   ```bash
   python scripts/run_all_scrapers.py
   ```

2. **Standardization**: Convert raw data to standardized format
   ```bash
   python scripts/standardize_json.py
   ```

3. **Migration**: Load standardized data into the database
   ```bash
   python scripts/migrate_to_db.py
   ```

## Complete Workflow

To run the entire process at once:
```bash
python scripts/workflow.py
```

## Individual Scrapers

Each scraper in `scrapers/` can be run individually:
```bash
cd data/scrapers
python motofan.py
```

The scrapers will save their output to `scraped_raw_data/` automatically.

## File Naming Convention

- Scrapers: `{retailer_name}.py`
- Raw data: `{retailer_name}.json`
- Standardized data: `standardized_{retailer_name}.json`
- Combined standardized data: `all_bikes_standardized.json`

## Directory Purposes

- **`scrapers/`**: Contains all individual scraper scripts
- **`scraped_raw_data/`**: Contains raw JSON files as scraped from websites (original format)
- **`standardized_data/`**: Contains processed JSON files with consistent field names and formats

## Notes

- Raw JSON files contain the original scraped data structure with varying field names
- Standardized files have consistent field names and formats for easy database migration
- The database contains the final, processed data used by the website
- The `all_bikes_standardized.json` file contains all bikes from all sources in one combined file 