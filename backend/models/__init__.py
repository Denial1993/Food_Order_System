"""
ORM 模型集中匯出

【import 順序說明】
food_food_category 必須在 food_data / food_category 之前匯入，
因為這兩個模型都用到 food_category_association 這個 Table 物件。
"""
from .food_food_category import food_category_association   # noqa: 確保中間表已加入 Base.metadata
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
    "food_category_association",
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
