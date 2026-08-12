"""Product list keyboard."""

from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.product import Product


class ProductListKeyboard:
    """Product list inline keyboard builder."""

    @staticmethod
    def get_product_list(products: List[Product]) -> InlineKeyboardMarkup:
        """Get product list inline keyboard."""
        keyboard = []
        for product in products:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"{product.name} - {int(product.price):,} تومان",
                        callback_data=f"select_product:{product.id}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_menu")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def get_product_confirmation(product_id: int) -> InlineKeyboardMarkup:
        """Get product confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(text="✅ تأیید و پرداخت", callback_data=f"confirm_product:{product_id}"),
                InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_order"),
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_products")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
