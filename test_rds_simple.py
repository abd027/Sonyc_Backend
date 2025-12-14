#!/usr/bin/env python3
"""Simple RDS connection test"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("RDS Connection Test")
print("=" * 60)

# Get environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_PASSWORD = os.getenv("DB_PASSWORD")

print(f"\n📋 Configuration:")
print(f"  DB_HOST: {DB_HOST}")
print(f"  DB_USER: {DB_USER}")
print(f"  DB_NAME: {DB_NAME}")
print(f"  DB_PORT: {DB_PORT}")
print(f"  DB_PASSWORD: {'*' * len(DB_PASSWORD) if DB_PASSWORD else 'Not set'}")

# Test if all required variables are set
required_vars = ["DB_HOST", "DB_USER", "DB_NAME", "DB_PASSWORD"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"\n❌ Missing required environment variables: {missing_vars}")
    sys.exit(1)

try:
    import psycopg2
    
    print(f"\n🔗 Attempting to connect to RDS...")
    print(f"   Connection string: postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    # Try to connect
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=10
    )
    
    cursor = conn.cursor()
    
    # Get PostgreSQL version
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    
    # Get database size
    cursor.execute("SELECT pg_database_size(current_database())")
    db_size_bytes = cursor.fetchone()[0]
    db_size_mb = db_size_bytes / (1024 * 1024)
    
    # List tables (if any)
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    
    print(f"\n✅ Successfully connected to RDS!")
    print(f"   PostgreSQL Version: {version.split(',')[0]}")
    print(f"   Database Size: {db_size_mb:.2f} MB")
    print(f"   Tables in database: {len(tables)}")
    
    if tables:
        print("   Table list:")
        for table in tables:
            print(f"     - {table[0]}")
    else:
        print("   No tables found. Database is empty.")
    
    cursor.close()
    conn.close()
    
    print(f"\n🎉 RDS connection test PASSED!")
    
except ImportError:
    print(f"\n❌ psycopg2 is not installed. Install it with:")
    print(f"   pip install psycopg2-binary")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Failed to connect to RDS: {e}")
    
    # Provide troubleshooting tips
    print(f"\n🔧 Troubleshooting steps:")
    print(f"   1. Check if RDS instance is running (AWS Console → RDS)")
    print(f"   2. Verify security group allows EC2 access on port 5432")
    print(f"   3. Check if DB_HOST endpoint is correct")
    print(f"   4. Verify username and password")
    print(f"   5. Check if database '{DB_NAME}' exists")
    
    # Network test suggestion
    print(f"\n🌐 Network test you can run:")
    print(f"   nc -zv {DB_HOST} {DB_PORT}")
    
    sys.exit(1)

print("=" * 60)
