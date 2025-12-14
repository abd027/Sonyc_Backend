from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment variable
# IMPORTANT: Change the default to your RDS URL!
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:abdullah13579@sonyc.cza2q88060bl.eu-north-1.rds.amazonaws.com:5432/sonyc"  # ← CHANGED THIS!
)

print(f"🔗 Using database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
