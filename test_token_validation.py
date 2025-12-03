#!/usr/bin/env python3
"""Comprehensive token validation test"""
import requests
import json
import time
from jose import jwt, JWTError
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")

def test_token_creation():
    """Test that tokens are created with correct format"""
    print("=" * 60)
    print("Test 1: Token Creation Format")
    print("=" * 60)
    
    # Create a new user
    email = f"test_validation_{int(time.time())}@example.com"
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": email,
            "password": "testpassword123"
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to create user: {response.text}")
        return None
    
    token = response.json().get('access_token')
    if not token:
        print("No token received")
        return None
    
    print(f"✓ Token received: {token[:30]}...")
    
    # Decode and verify format
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('sub')
        
        # Check if sub is string
        if isinstance(user_id, str):
            print(f"✓ Token 'sub' field is string: '{user_id}'")
        else:
            print(f"✗ ERROR: Token 'sub' field is {type(user_id).__name__}, expected string!")
            return None
        
        # Check if sub can be converted to int (for user lookup)
        try:
            user_id_int = int(user_id)
            print(f"✓ User ID can be converted to int: {user_id_int}")
        except ValueError:
            print(f"✗ ERROR: User ID '{user_id}' cannot be converted to int!")
            return None
        
        print(f"✓ Token expiration: {payload.get('exp')}")
        return token
        
    except JWTError as e:
        print(f"✗ ERROR: Token validation failed: {e}")
        return None

def test_token_extraction(token):
    """Test token extraction from Authorization header"""
    print("\n" + "=" * 60)
    print("Test 2: Token Extraction from Header")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        user_data = response.json()
        print(f"✓ Token extracted successfully")
        print(f"✓ User data: {user_data}")
        return True
    else:
        print(f"✗ ERROR: Token extraction failed: {response.text}")
        return False

def test_token_validation(token):
    """Test token validation logic"""
    print("\n" + "=" * 60)
    print("Test 3: Token Validation Logic")
    print("=" * 60)
    
    # Test with valid token
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/chats", headers=headers)
    
    if response.status_code == 200:
        print("✓ Valid token accepted")
        chats = response.json()
        print(f"✓ Retrieved {len(chats)} chats")
    else:
        print(f"✗ ERROR: Valid token rejected: {response.text}")
        return False
    
    # Test with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
    response = requests.get(f"{BASE_URL}/chats", headers=invalid_headers)
    
    if response.status_code == 401:
        print("✓ Invalid token correctly rejected")
    else:
        print(f"✗ ERROR: Invalid token was accepted (status: {response.status_code})")
        return False
    
    # Test with missing token
    response = requests.get(f"{BASE_URL}/chats")
    
    if response.status_code == 401:
        print("✓ Missing token correctly rejected")
    else:
        print(f"✗ ERROR: Missing token was accepted (status: {response.status_code})")
        return False
    
    return True

def test_user_lookup(token):
    """Test user lookup from token"""
    print("\n" + "=" * 60)
    print("Test 4: User Lookup from Token")
    print("=" * 60)
    
    # Decode token to get user ID
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id_str = payload.get('sub')
        user_id_int = int(user_id_str)
        
        # Test /auth/me endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✓ User lookup successful")
            print(f"  User ID from token: {user_id_int}")
            print(f"  User ID from API: {user_data.get('id')}")
            print(f"  User email: {user_data.get('email')}")
            
            if user_data.get('id') == user_id_int:
                print("✓ Token user ID matches API response")
                return True
            else:
                print(f"✗ ERROR: User ID mismatch!")
                return False
        else:
            print(f"✗ ERROR: User lookup failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Comprehensive Token Validation Test")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Token creation
    token = test_token_creation()
    results.append(("Token Creation", token is not None))
    
    if token:
        # Test 2: Token extraction
        results.append(("Token Extraction", test_token_extraction(token)))
        
        # Test 3: Token validation
        results.append(("Token Validation", test_token_validation(token)))
        
        # Test 4: User lookup
        results.append(("User Lookup", test_user_lookup(token)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("All tests passed!")
        exit(0)
    else:
        print("Some tests failed!")
        exit(1)

