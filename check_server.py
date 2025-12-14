import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("Checking backend server...")

try:
    from app.database import engine
    print("[OK] Database module imported")
    
    # Try to connect (this will fail if DB is not set up, but that's OK for now)
    try:
        conn = engine.connect()
        print("[OK] Database connection successful")
        conn.close()
    except Exception as e:
        print(f"[WARN] Database connection failed (expected if DB not set up): {e}")
    
except Exception as e:
    print(f"[ERROR] Database import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.main import app
    print(f"[OK] FastAPI app imported")
    print(f"[OK] App title: {app.title}")
    print(f"[OK] Number of routes: {len(app.routes)}")
    print(f"[OK] Routes:")
    for route in app.routes[:5]:
        if hasattr(route, 'path'):
            print(f"  - {route.path}")
except Exception as e:
    print(f"[ERROR] App import failed: {e}")
    import traceback
    traceback.print_exc()

print("\nBackend check complete!")









