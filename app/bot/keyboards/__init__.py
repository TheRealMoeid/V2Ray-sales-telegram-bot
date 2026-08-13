"""Bot keyboards package."""

from .main_menu import MainKeyboard
from .admin_menu import AdminMenuKeyboard
from .product_list import ProductListKeyboard
from .payment_info import PaymentInfoKeyboard
from .user_orders import UserOrdersKeyboard
from .admin_orders import AdminOrdersKeyboard
from .admin_config import AdminConfigKeyboard

__all__ = [
    "MainKeyboard",
    "AdminMenuKeyboard",
    "ProductListKeyboard",
    "PaymentInfoKeyboard",
    "UserOrdersKeyboard",
    "AdminOrdersKeyboard",
    "AdminConfigKeyboard",
]
