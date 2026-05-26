"""
認證 API：登入、查目前使用者

【流程】
1. 前端送 POST /api/auth/login，body 用 OAuth2 標準格式（form data）：
     username=admin&password=admin123
2. 後端比對 bcrypt 密碼，成功就回一張 JWT。
3. 前端把 JWT 存在 sessionStorage（關瀏覽器就清掉），之後每次請求都帶
   Authorization: Bearer <jwt>。
4. 想看自己是誰時呼叫 GET /api/auth/me。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.security import (
    create_access_token,
    get_current_user,
    verify_password,
)
from database import get_db
from models import FoodUser

router = APIRouter()


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """
    用 OAuth2PasswordRequestForm 是 FastAPI 標準寫法，
    好處是 Swagger 會自動顯示 Authorize 按鈕，方便測試。

    前端送的 Content-Type 必須是 application/x-www-form-urlencoded。
    """
    user: FoodUser | None = (
        db.query(FoodUser)
        .filter(
            FoodUser.Account == form.username,
            FoodUser.UserType == "S",            # 顧客不能從這裡登入
            FoodUser.StatusCode == "111",
        )
        .first()
    )

    # 帳號不存在、無密碼、密碼錯誤 → 統一回同一個錯誤訊息
    # （避免攻擊者用錯誤訊息分辨「帳號存不存在」）
    if not user or not user.Password or not verify_password(form.password, user.Password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user.UserID)
    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "UserID":   user.UserID,
            "Account":  user.Account,
            "UserName": user.UserName,
            "UserType": user.UserType,
        },
    }


@router.get("/me")
def me(user: FoodUser = Depends(get_current_user)) -> dict:
    """回傳目前登入者資訊。前端重整頁面時用來確認 token 還有效。"""
    return {
        "UserID":   user.UserID,
        "Account":  user.Account,
        "UserName": user.UserName,
        "UserType": user.UserType,
    }
