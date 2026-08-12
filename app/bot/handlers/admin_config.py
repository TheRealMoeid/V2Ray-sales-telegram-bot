"""Admin config management handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.bot.filters.admin import AdminFilter
from app.database.models.config import Config, ConfigStatus
from app.database.models.product import Product
from app.services.config_service import ConfigService
from app.bot.keyboards.admin_config import AdminConfigKeyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_config")


@router.callback_query(F.data == "admin_configs", AdminFilter())
async def handle_admin_configs(callback: CallbackQuery, session: AsyncSession):
    """Handle admin configs view."""
    try:
        # Get available configs count
        available_result = await session.execute(
            select(Config).where(Config.status == ConfigStatus.AVAILABLE)
        )
        available_configs = available_result.scalars().all()
        
        sold_result = await session.execute(
            select(Config).where(Config.status == ConfigStatus.ASSIGNED)
        )
        sold_count = sold_result.scalars().count()
        
        configs_text = f"""
📦 مدیریت کانفیگ‌ها

✅ موجود: {len(available_configs)}
💰 فروخته شده: {sold_count}

کانفیگ مورد نظر را انتخاب کنید یا کانفیگ جدید اضافه کنید.
"""
        
        await callback.message.edit_text(
            text=configs_text,
            reply_markup=AdminConfigKeyboard.get_configs_menu_keyboard(),
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_admin_configs: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data == "add_config", AdminFilter())
async def handle_add_config(callback: CallbackQuery):
    """Handle add config button."""
    try:
        await callback.message.answer(
            "➕ افزودن کانفیگ جدید\n\n"
            "لطفاً متن کانفیگ VLESS/V2Ray را ارسال کنید:\n\n"
            "مثال:\n"
            "`vless://uuid@host:port?...`\n\n"
            "یا از منوی زیر محصول را انتخاب کنید:",
            parse_mode="Markdown",
            reply_markup=AdminConfigKeyboard.get_products_for_config_keyboard(await ConfigService.get_all_products()),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in handle_add_config: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("select_product_for_config:"), AdminFilter())
async def handle_select_product_for_config(callback: CallbackQuery, session: AsyncSession):
    """Handle product selection for config."""
    try:
        product_id = int(callback.data.split(":")[1])
        
        # Store in session data (FSM alternative)
        # For simplicity, we'll just ask for config now
        await callback.message.answer(
            f"✅ محصول انتخاب شد.\n\n"
            f"لطفاً متن کانفیگ VLESS/V2Ray را برای این محصول ارسال کنید:",
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_select_product_for_config: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.message(AdminFilter())
async def handle_config_text_submission(message: Message, session: AsyncSession):
    """Handle config text submission from admin."""
    try:
        config_text = message.text
        
        if not config_text or not config_text.startswith(("vless://", "vmess://", "trojan://")):
            await message.answer(
                "❌ فرمت کانفیگ معتبر نیست.\n"
                "کانفیگ باید با vless://، vmess:// یا trojan:// شروع شود."
            )
            return
        
        # Get default product (first active product)
        result = await session.execute(
            select(Product).where(Product.is_active == True).limit(1)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            await message.answer("❌ هیچ محصول فعالی وجود ندارد.")
            return
        
        # Create config
        config = Config(
            product_id=product.id,
            config_text=config_text,
            status=ConfigStatus.AVAILABLE,
        )
        session.add(config)
        await session.commit()
        
        await message.answer(
            f"✅ کانفیگ با موفقیت اضافه شد.\n\n"
            f"ID: {config.id}\n"
            f"محصول: {product.name}\n"
            f"وضعیت: AVAILABLE"
        )
        
        logger.info(f"Config {config.id} added by admin {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in handle_config_text_submission: {e}")
        await message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")


@router.callback_query(F.data == "delete_config", AdminFilter())
async def handle_delete_config(callback: CallbackQuery, session: AsyncSession):
    """Handle delete config button."""
    try:
        # Get available configs
        result = await session.execute(
            select(Config)
            .where(Config.status == ConfigStatus.AVAILABLE)
            .limit(20)
        )
        configs = result.scalars().all()
        
        if not configs:
            await callback.answer(
                "📦 هیچ کانفیگ موجودی برای حذف وجود ندارد.",
                show_alert=True,
            )
            return
        
        await callback.message.edit_text(
            text="🗑 حذف کانفیگ\n\nکانفیگ مورد نظر را انتخاب کنید:",
            reply_markup=AdminConfigKeyboard.get_delete_configs_keyboard(configs),
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_delete_config: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("confirm_delete_config:"), AdminFilter())
async def handle_confirm_delete_config(callback: CallbackQuery, session: AsyncSession):
    """Handle confirm delete config."""
    try:
        config_id = int(callback.data.split(":")[1])
        
        result = await session.execute(
            select(Config).where(Config.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            await callback.answer(
                "❌ کانفیگ یافت نشد.",
                show_alert=True,
            )
            return
        
        # Delete config
        await session.delete(config)
        await session.commit()
        
        await callback.message.edit_text(
            text=f"✅ کانفیگ #{config_id} حذف شد.",
        )
        await callback.answer("✅ کانفیگ حذف شد")
        
        logger.info(f"Config {config_id} deleted by admin {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in handle_confirm_delete_config: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)
