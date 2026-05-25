# auth/security.py
from .config import settings
from datetime import datetime, timedelta
from typing import Optional

from argon2 import PasswordHasher
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from auth.context import current_user_var
# =========================
# 密码哈希（Argon2）
# =========================

ph = PasswordHasher()

def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    try:
        return ph.verify(hashed_password, plain_password)
    except Exception:
        return False


# =========================
# OAuth2 & JWT
# =========================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
):
    to_encode = data.copy()
    expire = (
        datetime.utcnow() + expires_delta
        if expires_delta
        else datetime.utcnow() + timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    # 将当前用户存储到 ContextVar 中
    current_user_var.set(user)

    return user
