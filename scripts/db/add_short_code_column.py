#!/usr/bin/env python3
"""
Migration script to add short_code column to comparisons table.
This adds URL shortening support for comparison sharing.
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(override=True)

from app import create_app
from app.extensions import db

def add_short_code_column():
    """Add short_code column to comparisons table"""
    print("="*60)
    print("🔧 ADDING SHORT_CODE COLUMN TO COMPARISONS TABLE")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        print(f"\n📊 Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        try:
            # Check database type
            engine = db.engine
            dialect = engine.dialect.name
            print(f"📊 Database dialect: {dialect}")
            
            # Check if column already exists
            if dialect == 'mysql':
                check_query = """
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'comparisons' 
                    AND COLUMN_NAME = 'short_code'
                """
            else:  # SQLite
                check_query = """
                    SELECT COUNT(*) as count 
                    FROM pragma_table_info('comparisons')
                    WHERE name = 'short_code'
                """
            
            result = db.session.execute(db.text(check_query))
            exists = result.fetchone()[0] > 0
            
            if exists:
                print("\n✅ Column 'short_code' already exists in 'comparisons' table")
                return True
            
            print("\n➕ Adding 'short_code' column to 'comparisons' table...")
            
            # Add the column (syntax differs slightly between MySQL and SQLite)
            if dialect == 'mysql':
                # MySQL: Add column and unique constraint separately
                db.session.execute(
                    db.text("""
                        ALTER TABLE comparisons 
                        ADD COLUMN short_code VARCHAR(10) NULL
                    """)
                )
                db.session.commit()
                
                # Add unique index
                db.session.execute(
                    db.text("""
                        CREATE UNIQUE INDEX idx_comparisons_short_code 
                        ON comparisons(short_code)
                    """)
                )
            else:  # SQLite
                # SQLite: Add column (unique constraint in column definition)
                db.session.execute(
                    db.text("""
                        ALTER TABLE comparisons 
                        ADD COLUMN short_code VARCHAR(10) UNIQUE
                    """)
                )
            
            db.session.commit()
            
            print("✅ Successfully added 'short_code' column!")
            print("\n📋 Column details:")
            print("   - Name: short_code")
            print("   - Type: VARCHAR(10)")
            print("   - Unique: Yes")
            print("   - Nullable: Yes (for backward compatibility)")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error adding column: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = add_short_code_column()
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

