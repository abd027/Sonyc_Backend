#!/usr/bin/env python3
"""Check what DATABASE_URL is actually being used"""
import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Checking DATABASE_URL")
print("=" * 40)

# Check from environment
env_url = os.getenv("DATABASE_URL")
print(f"1. From os.getenv('DATABASE_URL'):")
print(f"   {env_url if env_url else 'NOT SET!'}")

# Check what app/database.py would use
from app.database import DATABASE_URL
print(f"\n2. From app.database.DATABASE_URL:")
print(f"   {DATABASE_URL}")

# Check if it's localhost
if "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL:
    print(f"\n❌ PROBLEM: Still using localhost!")
    print(f"   This means DATABASE_URL env variable is not being loaded properly.")
    
    # Show the actual .env file path being used
    import dotenv
    dotenv_path = dotenv.find_dotenv()
    print(f"\n📁 .env file being used: {dotenv_path}")
    if dotenv_path and os.path.exists(dotenv_path):
        with open(dotenv_path, 'r') as f:
            content = f.read()
            if "DATABASE_URL" in content:
                print("   DATABASE_URL is in .env file")
            else:
                print("   DATABASE_URL is NOT in .env file")
else:
    print(f"\n✅ GOOD: Using RDS (not localhost)")
    
print("\n" + "=" * 40)
