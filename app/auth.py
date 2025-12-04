from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Password hashing - configure to handle long passwords
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",  # Use bcrypt version 2b
    bcrypt__rounds=12,   # Standard number of rounds
)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# HTTP Bearer scheme for token extraction
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password - handles bcrypt 72-byte limit"""
    # Bcrypt has a hard 72-byte limit. Always truncate to 71 bytes to be safe.
    # This is secure because bcrypt only uses the first 72 bytes anyway.
    if not isinstance(password, str):
        password = str(password)
    
    # Encode to bytes and truncate if needed
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 71:
        password_bytes = password_bytes[:71]
        password = password_bytes.decode('utf-8', errors='ignore')
    
    # Hash the password - wrap in try/except as final safety
    try:
        return pwd_context.hash(password)
    except ValueError as e:
        error_str = str(e).lower()
        # If it's a 72-byte error, truncate more aggressively
        if "72" in error_str or "bytes" in error_str:
            # Truncate to 70 bytes
            password_bytes = password.encode('utf-8')[:70]
            password = password_bytes.decode('utf-8', errors='ignore')
            return pwd_context.hash(password)
        # Re-raise other ValueError
        raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def extract_token_from_header(request: Request) -> Optional[str]:
    """Manually extract token from Authorization header as fallback"""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        return token
    except ValueError:
        return None


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get token from HTTPBearer first
    token = None
    if credentials is not None:
        token = credentials.credentials
    
    # Fallback: manually extract from header if HTTPBearer didn't work
    if not token:
        token = extract_token_from_header(request)
    
    if not token:
        logger.warning("No token provided in request")
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token payload missing 'sub' field")
            raise credentials_exception
        user_id_int = int(user_id)
    except JWTError as e:
        # Token is invalid or expired
        logger.warning(f"JWT validation failed: {str(e)}")
        raise credentials_exception
    except ValueError as e:
        # Invalid user ID format
        logger.warning(f"Invalid user ID format in token: {str(e)}")
        raise credentials_exception
    
    try:
        user = db.query(User).filter(User.id == user_id_int).first()
        if user is None:
            logger.warning(f"User not found for ID: {user_id_int}")
            raise credentials_exception
        return user
    except Exception as e:
        # Database error
        logger.error(f"Database error while fetching user: {str(e)}")
        raise credentials_exception

