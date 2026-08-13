"""User command handlers."""
import logging
<<<<<<< HEAD
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.bot.keyboards.main_menu import MainKeyboard
from app.services.user_service import UserService
=======

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.bot.keyboards.main_menu import MainKeyboard
>>>>>>> 1f3dccd (fix: apply full code review fixes (bugs 1-23))
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
<<<<<<< HEAD
        
        await message.answer(
            text=welcome_text,
            reply_markup=MainKeyboard.get_menu(),
        )
        
        logger.info(f"User {message.from_user.id} started the bot")
        
=======

        await message.answer(text=welcome_text, reply_markup=MainKeyboard.get_menu())

        action = "registered" if created else "started"
        logger.info(f"User {user_obj.id} {action}")

>>>>>>> 1f3dccd (fix: apply full code review fixes (bugs 1-23))
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
<<<<<<< HEAD
    """Handle back to main menu callback."""
    try:
        await callback.message.edit_text(
            text="🏠 منوی اصلی",
            reply_markup=MainKeyboard.get_menu(),
        )
=======
    """Handle back to main menu callback.

    Telegram API does not allow ReplyKeyboardMarkup on edit_message_text.
    So we edit the text without keyboard, then send a new message with the keyboard.
    """
    try:
        msg = callback.message
        if msg is None:
            await callback.answer()
            return

        # Edit the message text without keyboard (Telegram API restriction)
        await msg.edit_text(text="🏠 منوی اصلی")

        # Send a new message with the reply keyboard
        await msg.answer(
            text="منوی اصلی:",
            reply_markup=MainKeyboard.get_menu()
        )

>>>>>>> 1f3dccd (fix: apply full code review fixes (bugs 1-23))
        await callback.answer()
    except Exception as e:
        logger.exception(f"Error in handle_back_to_menu: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)