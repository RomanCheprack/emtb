#!/usr/bin/env python3
"""
Script to verify MySQL connection and .env configuration
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
import pymysql

def verify_connection():
    """Verify MySQL connection using .env configuration"""
    
    print("=" * 60)
    print("🔍 MySQL Connection Verification")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Get database URI
    db_uri = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    
    if not db_uri:
        print("\n❌ ERROR: No database URI found in .env file")
        print("   Please add SQLALCHEMY_DATABASE_URI to your .env file")
        print("\n   Format: mysql+pymysql://username:password@host:port/database")
        print("   Example: mysql+pymysql://root:mypassword@localhost:3306/myappdb")
        return False
    
    print(f"\n📋 Database URI found:")
    # Mask password for display
    display_uri = db_uri
    if '@' in display_uri:
        parts = display_uri.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split('//')[-1]
            if ':' in user_pass:
                user = user_pass.split(':')[0]
                display_uri = display_uri.replace(user_pass, f"{user}:***")
    
    print(f"   {display_uri}\n")
    
    # Parse URI
    if not db_uri.startswith('mysql'):
        print("⚠️  WARNING: Database URI doesn't start with 'mysql'")
        print(f"   Found: {db_uri[:20]}...")
        print("   Expected: mysql+pymysql://...")
        return False
    
    try:
        # Extract connection details
        # Format: mysql+pymysql://user:pass@host:port/database
        uri_parts = db_uri.replace('mysql+pymysql://', '')
        
        if '@' not in uri_parts:
            print("❌ Invalid URI format: missing '@'")
            return False
        
        user_pass, host_db = uri_parts.split('@', 1)
        
        if ':' not in user_pass:
            print("❌ Invalid URI format: missing ':' in user:password")
            return False
        
        username, password = user_pass.split(':', 1)
        
        if '/' not in host_db:
            print("❌ Invalid URI format: missing '/' before database name")
            return False
        
        host_port, database = host_db.split('/', 1)
        
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
            port = 3306
        
        print("🔧 Connection Details:")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Username: {username}")
        print(f"   Password: {'*' * len(password)}")
        print(f"   Database: {database}")
        
        # Try to connect
        print("\n🔌 Testing connection...")
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("✅ Connection successful!")
        
        # Test database
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE();")
            result = cursor.fetchone()
            print(f"\n📊 Connected to database: {result['DATABASE()']}")
            
            # Check tables
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            
            if tables:
                print(f"\n📋 Found {len(tables)} tables:")
                for table in tables:
                    table_name = list(table.values())[0]
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name};")
                    count = cursor.fetchone()['count']
                    print(f"   - {table_name}: {count} rows")
            else:
                print("\n⚠️  No tables found in database")
                print("   Run: python scripts/db/create_mysql_schema.py")
        
        connection.close()
        
        print("\n" + "=" * 60)
        print("✅ MySQL connection verified successfully!")
        print("=" * 60)
        
        return True
        
    except pymysql.err.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check if MySQL service is running")
        print("   2. Verify username and password")
        print("   3. Ensure database exists")
        print("   4. Check firewall settings")
        return False
        
    except ValueError as e:
        print(f"\n❌ Invalid URI format: {e}")
        print("\n   Expected format:")
        print("   mysql+pymysql://username:password@host:port/database")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_connection()
    sys.exit(0 if success else 1)

