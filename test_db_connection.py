#!/usr/bin/env python3
"""Test database connection"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("Database Connection Test")
print("=" * 50)

try:
    from app.database import engine, Base
    from app.models import User, Chat, Message
    
    print("\n[1] Testing database connection...")
    with engine.connect() as conn:
        print("  [OK] Database connection successful!")
    
    print("\n[2] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("  [OK] Tables created successfully!")
    
    print("\n[3] Verifying tables exist...")
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"  [OK] Found {len(tables)} tables:")
    for table in tables:
        print(f"      - {table}")
    
    print("\n" + "=" * 50)
    print("Database setup complete!")
    print("=" * 50)
    
except Exception as e:
    print(f"\n[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)





