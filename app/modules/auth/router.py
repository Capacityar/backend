from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from .schemas import RegisterIn, LoginIn, TokenOut
from . import service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        user = service.register_user(db, payload)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")
    return TokenOut(
        access_token=service.create_access_token(user.id),
        refresh_token=service.create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    return TokenOut(
        access_token=service.create_access_token(user.id),
        refresh_token=service.create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenOut)
def refresh(token: TokenOut):
    user_id = service.decode_token(token.refresh_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")
    return TokenOut(
        access_token=service.create_access_token(user_id),
        refresh_token=service.create_refresh_token(user_id),
    )
