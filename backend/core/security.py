"""
認證安全工具：bcrypt 密碼雜湊 + JWT 簽發/驗證 + FastAPI 依賴

【給新手】
- bcrypt：密碼「單向雜湊」，存進 DB 的不是明文，是雜湊結果。
- JWT：登入成功後給前端一張「通行證」，之後每次 API 都帶在 Authorization header。
- get_current_admin_user：FastAPI 依賴，掛到路由上就會強制驗證 token。
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.config import settings
from database import get_db
from models import FoodUser


# OAuth2PasswordBearer 讓 Swagger 自動出現 Authorize 按鈕
# tokenUrl 是給 Swagger 知道「去哪取 token」用的相對路徑
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# bcrypt 規定密碼最多 72 bytes，超過會直接 raise；先截掉避免 ValueError
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def verify_password(plain: str, hashed: str) -> bool:
    """檢查明文密碼是否符合 DB 裡的雜湊"""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # 雜湊格式錯誤都當作驗證失敗（不要把例外曝給呼叫端）
        return False


def hash_password(plain: str) -> str:
    """產生新雜湊（建立帳號 / 改密碼時使用）"""
    return bcrypt.hashpw(_to_bcrypt_bytes(plain), bcrypt.gensalt(rounds=12)).decode("utf-8")


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """
    產生 JWT。
    subject = 通常放 UserID（字串化）；之後解 token 就能反查使用者。
    """
    exp_minutes = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _credentials_error(msg: str = "認證失敗，請重新登入") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=msg,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> FoodUser:
    """解析 token → 撈出 DB 裡的使用者。任何錯誤一律回 401。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise _credentials_error()
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise _credentials_error()

    user: FoodUser | None = (
        db.query(FoodUser)
        .filter(FoodUser.UserID == user_id, FoodUser.StatusCode == "111")
        .first()
    )
    if not user:
        raise _credentials_error("帳號已停用或不存在")
    return user


def get_current_admin_user(user: FoodUser = Depends(get_current_user)) -> FoodUser:
    """只放行 UserType='S'（店家）。顧客即使有 token 也不能進後台。"""
    if user.UserType != "S":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此帳號無後台權限",
        )
    return user
