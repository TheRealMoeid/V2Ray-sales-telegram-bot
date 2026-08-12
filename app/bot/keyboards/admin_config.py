"""Admin config keyboard."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.config import Config
from app.database.models.product import Product


class AdminConfigKeyboard:
    """Admin config inline keyboard builder."""

    @staticmethod
    def get_configs_menu_keyboard() -> InlineKeyboardMarkup:
        """Get configs management menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(text="➕ افزودن کانفیگ", callback_data="add_config"),
            ],
            [
                InlineKeyboardButton(text="🗑 حذف کانفیگ", callback_data="delete_config"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel"),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_products_for_config_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
        """Get products keyboard for config addition."""
        keyboard = []
        
        for product in products[:10]:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📦 {product.name}",
                    callback_data=f"select_product_for_config:{product.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_configs")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_delete_configs_keyboard(configs: list[Config]) -> InlineKeyboardMarkup:
        """Get delete configs keyboard."""
        keyboard = []
        
        for config in configs[:15]:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"کانفیگ #{config.id}",
                    callback_data=f"confirm_delete_config:{config.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_configs")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
