import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.modules.users import repository as user_repo
from app.modules.users.models import User, UserRole
from .schemas import RegisterIn

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insecure-secret-key")
ALGORITHM = "HS256"
ACCESS_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def register_user(db: Session, data: RegisterIn) -> User:
    user = User(
        first_name="",
        last_name="",
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=UserRole(data.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = user_repo.find_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def _make_token(data: dict, delta: timedelta) -> str:
    payload = {**data, "exp": datetime.utcnow() + delta}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _make_token({"sub": str(user_id)}, timedelta(minutes=ACCESS_EXPIRE_MIN))


def create_refresh_token(user_id: int) -> str:
    return _make_token({"sub": str(user_id)}, timedelta(days=REFRESH_EXPIRE_DAYS))


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub else None
    except JWTError:
        return None
