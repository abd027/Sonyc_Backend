#!/usr/bin/env python3
"""Test script to verify backend setup"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 50)
print("Backend Setup Verification")
print("=" * 50)

# Test 1: Environment variables
print("\n[1] Checking environment variables...")
google_key = os.getenv("GOOGLE_API_KEY")
jwt_secret = os.getenv("JWT_SECRET_KEY")
db_url = os.getenv("DATABASE_URL")

if google_key:
    print(f"  [OK] GOOGLE_API_KEY: Found (length: {len(google_key)})")
else:
    print("  [FAIL] GOOGLE_API_KEY: Not found")

if jwt_secret:
    print(f"  [OK] JWT_SECRET_KEY: Found (length: {len(jwt_secret)})")
else:
    print("  [FAIL] JWT_SECRET_KEY: Not found")

if db_url:
    print(f"  [OK] DATABASE_URL: Found")
else:
    print("  [WARN] DATABASE_URL: Using default")

# Test 2: Embedding model initialization
print("\n[2] Testing embedding model initialization...")
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    print("  [OK] Embedding model initialized successfully")
except Exception as e:
    print(f"  [FAIL] Failed to initialize embedding model: {e}")

# Test 3: Database connection (optional)
print("\n[3] Testing database connection (optional)...")
try:
    from app.database import engine
    with engine.connect() as conn:
        print("  [OK] Database connection successful")
except Exception as e:
    print(f"  [WARN] Database connection failed (this is OK if PostgreSQL is not set up): {e}")

# Test 4: FastAPI app import
print("\n[4] Testing FastAPI app import...")
try:
    from app.main import app
    print(f"  [OK] FastAPI app imported successfully")
    print(f"     App title: {app.title}")
    print(f"     Number of routes: {len(app.routes)}")
except Exception as e:
    print(f"  [FAIL] Failed to import app: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Setup verification complete!")
print("=" * 50)

