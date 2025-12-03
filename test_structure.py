"""
Test script to verify backend structure and logic without requiring all dependencies
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all imports are correct"""
    print("Testing imports...")
    try:
        from app.database import get_db, Base, engine
        print("[OK] Database imports OK")
    except Exception as e:
        print(f"[FAIL] Database imports failed: {e}")
        return False
    
    try:
        from app.models import User, Chat, Message
        print("[OK] Models imports OK")
    except Exception as e:
        print(f"[FAIL] Models imports failed: {e}")
        return False
    
    try:
        from app.auth import (
            get_password_hash,
            verify_password,
            create_access_token,
            get_current_user,
            ACCESS_TOKEN_EXPIRE_MINUTES
        )
        print("[OK] Auth imports OK")
    except Exception as e:
        print(f"[FAIL] Auth imports failed: {e}")
        return False
    
    return True

def test_auth_functions():
    """Test authentication functions"""
    print("\nTesting auth functions...")
    try:
        from app.auth import get_password_hash, verify_password
        
        # Test password hashing
        password = "test123"
        hashed = get_password_hash(password)
        print(f"[OK] Password hashing works (hash length: {len(hashed)})")
        
        # Test password verification
        if verify_password(password, hashed):
            print("[OK] Password verification works")
        else:
            print("[FAIL] Password verification failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Auth functions test failed: {e}")
        return False

def test_models_structure():
    """Test that models have correct structure"""
    print("\nTesting models structure...")
    try:
        from app.models import User, Chat, Message
        
        # Check User model
        assert hasattr(User, 'id'), "User model missing 'id'"
        assert hasattr(User, 'email'), "User model missing 'email'"
        assert hasattr(User, 'password_hash'), "User model missing 'password_hash'"
        assert hasattr(User, 'created_at'), "User model missing 'created_at'"
        print("[OK] User model structure OK")
        
        # Check Chat model
        assert hasattr(Chat, 'id'), "Chat model missing 'id'"
        assert hasattr(Chat, 'user_id'), "Chat model missing 'user_id'"
        assert hasattr(Chat, 'title'), "Chat model missing 'title'"
        assert hasattr(Chat, 'type'), "Chat model missing 'type'"
        assert hasattr(Chat, 'vector_db_collection_id'), "Chat model missing 'vector_db_collection_id'"
        print("[OK] Chat model structure OK")
        
        # Check Message model
        assert hasattr(Message, 'id'), "Message model missing 'id'"
        assert hasattr(Message, 'chat_id'), "Message model missing 'chat_id'"
        assert hasattr(Message, 'role'), "Message model missing 'role'"
        assert hasattr(Message, 'content'), "Message model missing 'content'"
        assert hasattr(Message, 'created_at'), "Message model missing 'created_at'"
        print("[OK] Message model structure OK")
        
        return True
    except Exception as e:
        print(f"✗ Models structure test failed: {e}")
        return False

def test_endpoint_definitions():
    """Test that endpoints are defined correctly"""
    print("\nTesting endpoint definitions...")
    try:
        # Read main.py and check for endpoint definitions
        with open('app/main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        endpoints = [
            ('@app.post("/auth/signup"', 'Signup endpoint'),
            ('@app.post("/auth/signin"', 'Signin endpoint'),
            ('@app.get("/auth/me"', 'Get current user endpoint'),
            ('@app.get("/chats"', 'Get chats endpoint'),
            ('@app.post("/chats"', 'Create chat endpoint'),
            ('@app.get("/chats/{chat_id}/messages"', 'Get messages endpoint'),
            ('@app.delete("/chats/{chat_id}"', 'Delete chat endpoint'),
            ('@app.post("/chat/stream"', 'Chat stream endpoint'),
            ('@app.post("/yt_rag"', 'YouTube RAG endpoint'),
            ('@app.post("/pdf_rag"', 'PDF RAG endpoint'),
            ('@app.post("/web_rag"', 'Web RAG endpoint'),
            ('@app.post("/git_rag"', 'Git RAG endpoint'),
        ]
        
        for pattern, name in endpoints:
            if pattern in content:
                print(f"[OK] {name} found")
            else:
                print(f"[FAIL] {name} NOT found")
                return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Endpoint definitions test failed: {e}")
        return False

def test_response_formats():
    """Test that endpoints return correct formats"""
    print("\nTesting response formats...")
    try:
        with open('app/main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check yt_rag returns collection_name
        if 'return {"collection_name": collection_name}' in content or '"collection_name"' in content:
            print("[OK] RAG endpoints return collection_name")
        else:
            print("[FAIL] RAG endpoints may not return collection_name correctly")
            return False
        
        # Check auth endpoints return token
        if 'return {"access_token":' in content or '"access_token"' in content:
            print("[OK] Auth endpoints return access_token")
        else:
            print("[FAIL] Auth endpoints may not return access_token correctly")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Response formats test failed: {e}")
        return False

def test_cors_middleware():
    """Test that CORS is configured"""
    print("\nTesting CORS configuration...")
    try:
        with open('app/main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if 'CORSMiddleware' in content and 'allow_origins' in content:
            print("[OK] CORS middleware configured")
            return True
        else:
            print("[FAIL] CORS middleware not found")
            return False
    except Exception as e:
        print(f"[FAIL] CORS test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Backend Structure and Logic Tests")
    print("=" * 50)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Auth Functions", test_auth_functions()))
    results.append(("Models Structure", test_models_structure()))
    results.append(("Endpoint Definitions", test_endpoint_definitions()))
    results.append(("Response Formats", test_response_formats()))
    results.append(("CORS Configuration", test_cors_middleware()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All structure tests passed!")
        sys.exit(0)
    else:
        print("\n[ERROR] Some tests failed")
        sys.exit(1)

