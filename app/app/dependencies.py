from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.models.user_model import User
from app.database import SessionLocal
import os

# Load JWT settings from environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")  # Replace in production
ALGORITHM = "HS256"

# OAuth2 scheme for API token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Retrieve current user via JWT token
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception
    return user

# Ensure a user is logged in via cookie
def require_admin(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not (user.is_admin or user.is_superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    return user

# Ensure current user is a superadmin
def require_superadmin(
    user: User = Depends(get_current_user)
) -> User:
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmins only"
        )
    return user
