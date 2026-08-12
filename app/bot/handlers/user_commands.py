"""User command handlers."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.bot.keyboards.main_menu import MainMenuKeyboard
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="user_commands")


@router.message(Command("start"))
async def handle_start(message: Message, session):
    """Handle /start command."""
    try:
        # Register or update user
        await UserService.register_or_update_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        await session.commit()
        
        # Send welcome message with main menu
        welcome_text = f"👋 سلام {message.from_user.first_name}!\n\n"
        welcome_text += "به فروشگاه کانفیگ V2Ray خوش آمدید.\n"
        welcome_text += "از منوی زیر می‌توانید خرید کنید یا سفارش‌های خود را مشاهده کنید."
        
        await message.answer(
            text=welcome_text,
            reply_markup=MainMenuKeyboard.get_main_menu_keyboard(),
        )
        
        logger.info(f"User {message.from_user.id} started the bot")
        
    except Exception as e:
        logger.error(f"Error in handle_start: {e}")
        await message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")


@router.message(Command("help"))
async def handle_help(message: Message, session):
    """Handle /help command."""
    help_text = """
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
@{support_username}
""".format(support_username="Moeid_TestBot")  # TODO: Get from settings
    
    await message.answer(text=help_text)


@router.callback_query(F.data == "back_to_menu")
async def handle_back_to_menu(callback: CallbackQuery, session):
    """Handle back to main menu callback."""
    try:
        await callback.message.edit_text(
            text="🏠 منوی اصلی",
            reply_markup=MainMenuKeyboard.get_main_menu_keyboard(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in handle_back_to_menu: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)
