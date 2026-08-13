"""User command handlers."""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import MainKeyboard
from app.database.session import async_session_maker
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="user_commands")


@router.message(Command("start"))
async def handle_start(message: Message):
    """Handle /start command."""
    if message.from_user is None:
        await message.answer("❌ خطا: اطلاعات کاربر در پیام موجود نیست.")
        return

    user_obj = message.from_user

    try:
        async with async_session_maker() as session:
            user_service = UserService(session)
            _user, created = await user_service.get_or_create_user(
                telegram_id=user_obj.id,
                username=user_obj.username,
                first_name=user_obj.first_name,
                last_name=user_obj.last_name,
            )
            await session.commit()

        welcome_text = f"👋 سلام {user_obj.first_name or 'دوست عزیز'}!\n\n"
        welcome_text += "به فروشگاه کانفیگ V2Ray خوش آمدید.\n"
        welcome_text += "از منوی زیر می‌توانید خرید کنید یا سفارش‌های خود را مشاهده کنید."

        await message.answer(text=welcome_text, reply_markup=MainKeyboard.get_menu())

        logger.info(f"User {user_obj.id} {'registered' if created else 'started'}")

    except Exception as e:
        logger.exception(f"Error in handle_start: {e}")
        await message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")


@router.message(Command("help"))
async def handle_help(message: Message):
    """Handle /help command."""
    try:
        from app.config.settings import settings
        support = (
            getattr(settings, "SUPPORT_USERNAME", None)
            or getattr(settings, "support_username", "@support")
        )
    except Exception:
        support = "@support"

    help_text = f"""
📚 راهنمای استفاده از ربات

🛒 خرید کانفیگ:
1. از منوی اصلی «خرید کانفیگ» را انتخاب کنید
2. محصول مورد نظر را انتخاب کنید
3. اطلاعات پرداخت را مشاهده کنید
4. مبلغ را کارت‌به‌کارت کنید
5. تصویر رسید را ارسال کنید
6. پس از تأیید ادمین، کانفیگ شما ارسال می‌شود

📋 سفارش‌های من:
می‌توانید وضعیت سفارش‌های خود را مشاهده کنید

💬 پشتیبانی:
برای پشتیبانی با آیدی زیر تماس بگیرید:
{support}
"""
    await message.answer(text=help_text)


@router.callback_query(F.data == "back_to_menu")
async def handle_back_to_menu(callback: CallbackQuery):
    """Handle back to main menu callback."""
    try:
        msg = callback.message
        if msg is None:
            await callback.answer()
            return

        await msg.edit_text(text="🏠 منوی اصلی")
        await msg.answer(text="منوی اصلی:", reply_markup=MainKeyboard.get_menu())
        await callback.answer()
    except Exception as e:
        logger.exception(f"Error in handle_back_to_menu: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)