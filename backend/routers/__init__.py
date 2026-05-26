from fastapi import APIRouter, Depends

from core.security import get_current_admin_user

from .tables import router as tables_router
from .menu import router as menu_router
from .cart import router as cart_router
from .orders import router as orders_router
from .auth import router as auth_router
from .admin import router as admin_router
from .ws import router as ws_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(tables_router, prefix="/tables", tags=["tables"])
api_router.include_router(menu_router, prefix="/menu", tags=["menu"])
api_router.include_router(cart_router, prefix="/cart", tags=["cart"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
# 後台路由整批掛上「必須是店家身分」依賴 — 沒帶 token 直接 401
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)],
)

__all__ = ["api_router", "ws_router"]
