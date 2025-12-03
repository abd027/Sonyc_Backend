#!/usr/bin/env python3
"""Test authentication endpoints"""
import requests
import json
from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")

def test_signup():
    """Test user signup"""
    print("=" * 50)
    print("Testing Signup")
    print("=" * 50)
    
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        print(f"Token received: {token[:20] if token else 'N/A'}...")
        
        # Verify token format
        if token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get('sub')
                print(f"Token payload verified - User ID (sub): {user_id} (type: {type(user_id).__name__})")
                if not isinstance(user_id, str):
                    print(f"WARNING: Token 'sub' field is not a string! It's: {type(user_id).__name__}")
            except Exception as e:
                print(f"WARNING: Could not decode token: {e}")
        
        return token
    else:
        print(f"Error: {response.text}")
        return None

def test_signin():
    """Test user signin"""
    print("\n" + "=" * 50)
    print("Testing Signin")
    print("=" * 50)
    
    response = requests.post(
        f"{BASE_URL}/auth/signin",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        print(f"Token received: {token[:20] if token else 'N/A'}...")
        
        # Verify token format
        if token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get('sub')
                print(f"Token payload verified - User ID (sub): {user_id} (type: {type(user_id).__name__})")
                if not isinstance(user_id, str):
                    print(f"WARNING: Token 'sub' field is not a string! It's: {type(user_id).__name__}")
            except Exception as e:
                print(f"WARNING: Could not decode token: {e}")
        
        return token
    else:
        print(f"Error: {response.text}")
        return None

def test_get_me(token):
    """Test getting current user"""
    print("\n" + "=" * 50)
    print("Testing GET /auth/me")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"User: {response.json()}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_get_chats(token):
    """Test getting chats"""
    print("\n" + "=" * 50)
    print("Testing GET /chats")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/chats",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        chats = response.json()
        print(f"Chats: {len(chats)} found")
        return True
    else:
        print(f"Error: {response.text}")
        return False

if __name__ == "__main__":
    print("\nTesting Authentication Flow\n")
    
    # Test signup
    token = test_signup()
    
    if not token:
        # Try signin if signup failed (user might already exist)
        token = test_signin()
    
    if token:
        # Test authenticated endpoints
        test_get_me(token)
        test_get_chats(token)
        print("\n" + "=" * 50)
        print("All tests completed!")
        print("=" * 50)
    else:
        print("\nFailed to get authentication token")

