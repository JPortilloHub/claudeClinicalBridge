"""Authentication router — login and user info."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.python.api import schemas
from src.python.api.dependencies import JWT_ALGORITHM, get_current_user
from src.python.api.models import User
from src.python.utils.config import settings
from src.python.utils.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_HOURS = 24


def _create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=JWT_ALGORITHM)


@router.post("/login", response_model=schemas.TokenResponse)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not pwd_context.verify(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    access_token = _create_access_token(data={"sub": user.username})

    return schemas.TokenResponse(
        access_token=access_token,
        user=schemas.UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        ),
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info from JWT token."""
    return current_user
