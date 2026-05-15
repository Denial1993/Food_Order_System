"""
認證 — placeholder。
規劃: JWT (HS256),帳號密碼 bcrypt 雜湊,/auth/login + /auth/me。
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
def login() -> dict[str, str]:
    return {"detail": "TODO: implement JWT login"}


@router.get("/me")
def me() -> dict[str, str]:
    return {"detail": "TODO: return current user"}
