"""ORM 模型集中匯出 — 匯入此 package 即會註冊所有表至 Base.metadata。"""
from .food_role import FoodRole
from .food_user import FoodUser
from .food_menu import FoodMenu
from .food_role_menu import FoodRoleMenu
from .food_table import FoodTable
from .food_category import FoodCategory
from .food_picture import FoodPicture
from .food_data import FoodData
from .food_cart import FoodCart
from .food_order import FoodOrder
from .food_order_detail import FoodOrderDetail
from .food_system_config import FoodSystemConfig

__all__ = [
    "FoodRole",
    "FoodUser",
    "FoodMenu",
    "FoodRoleMenu",
    "FoodTable",
    "FoodCategory",
    "FoodPicture",
    "FoodData",
    "FoodCart",
    "FoodOrder",
    "FoodOrderDetail",
    "FoodSystemConfig",
]
