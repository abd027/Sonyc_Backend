#!/usr/bin/env python3
"""Debug authentication token"""
import requests
import json
from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")

# Get a token (try signup first, then signin)
print("Getting token...")
response = requests.post(
    f"{BASE_URL}/auth/signup",
    json={
        "email": "debug@example.com",
        "password": "testpassword123"
    }
)

if response.status_code != 200:
    # User might already exist, try signin
    print("Signup failed, trying signin...")
    response = requests.post(
        f"{BASE_URL}/auth/signin",
        json={
            "email": "debug@example.com",
            "password": "testpassword123"
        }
    )

if response.status_code != 200:
    print(f"Failed to get token: {response.text}")
    exit(1)

token = response.json().get('access_token')
print(f"Token: {token[:50]}...")

# Decode token
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    print(f"\nToken payload: {json.dumps(payload, indent=2)}")
    user_id = payload.get('sub')
    print(f"User ID (sub): {user_id}")
    print(f"User ID type: {type(user_id).__name__}")
    
    # Verify it's a string
    if isinstance(user_id, str):
        print("✓ Token 'sub' field is correctly formatted as string")
    else:
        print(f"✗ ERROR: Token 'sub' field is {type(user_id).__name__}, expected string!")
except Exception as e:
    print(f"Failed to decode token: {e}")

# Test with token
print("\nTesting /auth/me endpoint...")
headers = {
    "Authorization": f"Bearer {token}"
}
print(f"Headers: {headers}")

response = requests.get(
    f"{BASE_URL}/auth/me",
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

