# Scripts Organization

This folder contains organized scripts for managing the eMTB website data pipeline.

## 📁 Folder Structure

### 🗄️ `db/` - Database Management
Scripts for database operations, migrations, and schema management.

- **`models.py`** - SQLAlchemy database models and connection utilities
- **`migrate_to_db.py`** - Migrate standardized JSON data to SQLite database
- **`migrate_database_schema.py`** - Handle database schema migrations
- **`recreate_bikes_table.py`** - Recreate bikes table with current schema and cleaned data (includes backup and data cleaning)

### 📊 `data/` - Data Processing
Scripts for processing and standardizing bike data.

- **`standardize_json.py`** - Standardize scraped JSON data with field mapping
- **`migrate_compare_counts.py`** - Migrate and manage bike comparison statistics

### 🕷️ `scrapers/` - Data Collection
Scripts for collecting bike data from various sources.

- **`run_all_scrapers.py`** - Execute all web scrapers to collect bike data

### 🔧 `maintenance/` - Maintenance Scripts
Scripts for fixing data issues and maintenance tasks.

- **`fix_database_quotes.py`** - Fix problematic characters in database (semicolons, quotes, etc.)
- **`fix_bike_ids.py`** - Clean bike IDs by removing URL-encoded characters

### 📋 Root Level
- **`workflow.py`** - Main workflow script for the entire data pipeline

## 🚀 Usage Examples

### Database Operations
```bash
# Recreate database with current schema
python scripts/db/recreate_bikes_table.py

# Migrate data to database
python scripts/db/migrate_to_db.py

# Run schema migrations
python scripts/db/migrate_database_schema.py
```

### Data Processing
```bash
# Standardize scraped data
python scripts/data/standardize_json.py

# Update comparison counts
python scripts/data/migrate_compare_counts.py
```

### Data Collection
```bash
# Run all scrapers
python scripts/scrapers/run_all_scrapers.py
```

### Maintenance
```bash
# Fix database character issues
python scripts/maintenance/fix_database_quotes.py

# Clean bike IDs
python scripts/maintenance/fix_bike_ids.py
```

### Complete Workflow
```bash
# Run the entire data pipeline
python scripts/workflow.py
```

## 📝 Notes

- **Database Backup**: The `recreate_bikes_table.py` script automatically creates a backup before making changes
- **Data Cleaning**: Most scripts include data cleaning functions to handle problematic characters
- **Error Handling**: Scripts include comprehensive error handling and rollback capabilities
- **Logging**: All scripts provide detailed logging of their operations

## 🔄 Typical Workflow

1. **Data Collection**: Run scrapers to collect raw data
2. **Data Processing**: Standardize the collected data
3. **Database Migration**: Migrate processed data to database
4. **Maintenance**: Run maintenance scripts if needed
5. **Verification**: Test the website functionality

## ⚠️ Important Notes

- Always backup your database before running maintenance scripts
- Some scripts will modify your database - review them before execution
- The `recreate_bikes_table.py` script will drop and recreate the bikes table
- Maintenance scripts should only be run when needed to fix specific issues
