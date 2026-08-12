"""Admin command handlers."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.bot.filters.admin import AdminFilter
from app.bot.keyboards.admin_menu import AdminMenuKeyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_commands")


@router.message(Command("admin"), AdminFilter())
async def handle_admin_panel(message: Message):
    """Handle /admin command for admins."""
    try:
        await message.answer(
            text="⚙️ پنل مدیریت\n\nگزینه مورد نظر را انتخاب کنید:",
            reply_markup=AdminMenuKeyboard.get_admin_menu_keyboard(),
        )
        logger.info(f"Admin {message.from_user.id} accessed admin panel")
    except Exception as e:
        logger.error(f"Error in handle_admin_panel: {e}")
        await message.answer("❌ خطایی رخ داد.")


@router.callback_query(F.data == "admin_panel", AdminFilter())
async def handle_admin_panel_callback(callback: CallbackQuery):
    """Handle admin panel button callback."""
    try:
        await callback.message.edit_text(
            text="⚙️ پنل مدیریت\n\nگزینه مورد نظر را انتخاب کنید:",
            reply_markup=AdminMenuKeyboard.get_admin_menu_keyboard(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in handle_admin_panel_callback: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)
