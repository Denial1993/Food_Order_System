from fastapi import APIRouter

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
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

__all__ = ["api_router", "ws_router"]
