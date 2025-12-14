#!/usr/bin/env python3
"""Simple test after fix"""
import os
from dotenv import load_dotenv

load_dotenv()

print("🧪 Testing after fix...")
print("=" * 40)

# Import and check
from app.database import DATABASE_URL, engine

print(f"1. DATABASE_URL being used:")
# Mask password for security
if "://" in DATABASE_URL:
    parts = DATABASE_URL.split("://")
    if "@" in parts[1]:
        user_host = parts[1].split("@")
        user_pass = user_host[0]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            masked = f"{parts[0]}://{user}:****@{user_host[1]}"
            print(f"   {masked}")
        else:
            print(f"   {DATABASE_URL}")
    else:
        print(f"   {DATABASE_URL}")
else:
    print(f"   {DATABASE_URL}")

# Test connection
print(f"\n2. Testing connection...")
try:
    with engine.connect() as conn:
        print("   ✅ Connection successful!")
        
        # Get database info
        result = conn.execute("SELECT current_database(), version()")
        db_name, version = result.fetchone()
        print(f"   📊 Connected to: {db_name}")
        print(f"   🐘 PostgreSQL: {version.split(',')[0]}")
        
except Exception as e:
    print(f"   ❌ Connection failed: {e}")

print("\n" + "=" * 40)
