"""Product purchase handlers."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.payment_info import PaymentInfoKeyboard
from app.bot.keyboards.product_list import ProductListKeyboard
from app.config.settings import settings
from app.database.models.config import Config, ConfigStatus
from app.database.models.order import Order, OrderStatus
from app.database.models.product import Product
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = Router(name="purchase")


@router.callback_query(F.data == "buy_config")
async def handle_buy_config(callback: CallbackQuery, session: AsyncSession):
    """Handle buy config button."""
    try:
        # Get active products
        result = await session.execute(
            select(Product).where(Product.is_active == True)
        )
        products = result.scalars().all()

        if not products:
            await callback.answer(
                "❌ در حال حاضر محصولی موجود نیست.",
                show_alert=True,
            )
            return

        # Send product list (Bug #11 fixed: get_product_list, not get_products_keyboard)
        await callback.message.edit_text(
            text="🛒 محصولات موجود:\n\nمحصول مورد نظر را انتخاب کنید:",
            reply_markup=ProductListKeyboard.get_product_list(products),
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_buy_config: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("select_product:"))
async def handle_select_product(callback: CallbackQuery, session: AsyncSession):
    """Handle product selection."""
    try:
        product_id = int(callback.data.split(":")[1])

        # Get product
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            await callback.answer(
                "❌ محصول یافت نشد.",
                show_alert=True,
            )
            return

        # Check available configs count
        configs_result = await session.execute(
            select(Config).where(
                Config.product_id == product_id,
                Config.status == ConfigStatus.AVAILABLE,
            )
        )
        available_configs = configs_result.scalars().all()

        if len(available_configs) == 0:
            await callback.answer(
                "❌ این محصول در حال حاضر ناموجود است.",
                show_alert=True,
            )
            return

        # Check if user has pending order (uses Telegram ID - compatible with Bug #3 fix)
        user_has_pending = await OrderService.user_has_pending_order(
            session=session,
            user_id=callback.from_user.id,
        )

        if user_has_pending:
            await callback.answer(
                "⚠️ شما یک سفارش در انتظار پرداخت دارید. لطفاً ابتدا آن را تکمیل کنید.",
                show_alert=True,
            )
            return

        # Create order (user_id here is Telegram ID - matches Bug #3 fix)
        order = await OrderService.create_order(
            session=session,
            user_id=callback.from_user.id,
            product_id=product_id,
            amount=product.price,
            currency="تومان",
        )
        await session.commit()

        # Send payment info
        payment_text = f"""
💳 اطلاعات پرداخت

📦 محصول: {product.name}
💰 مبلغ: {product.price:,} {product.currency}
⏱ مدت: {product.duration} روز

━━━━━━━━━━━━━━━━━━━━

شماره کارت:
`{settings.bank_card_number}`

به نام:
{settings.bank_account_name}

بانک:
{settings.bank_name}

━━━━━━━━━━━━━━━━━━━━

بعد از پرداخت، تصویر رسید را همینجا ارسال کنید.
"""

        await callback.message.edit_text(
            text=payment_text,
            reply_markup=PaymentInfoKeyboard.get_payment_info_keyboard(),
        )
        await callback.answer()

        logger.info(f"Order {order.id} created for user {callback.from_user.id}")

    except Exception as e:
        logger.exception(f"Error in handle_select_product: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data == "retry_payment")
async def handle_retry_payment(callback: CallbackQuery, session: AsyncSession):
    """Handle retry payment."""
    try:
        # Get user's pending order (uses Telegram ID - compatible with Bug #3 fix)
        result = await session.execute(
            select(Order)
            .where(Order.user_id == callback.from_user.id)
            .where(
                Order.status.in_(
                    [OrderStatus.PENDING_PAYMENT, OrderStatus.RECEIPT_SUBMITTED]
                )
            )
            .order_by(Order.created_at.desc())
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer(
                "❌ سفارش فعالی ندارید.",
                show_alert=True,
            )
            return

        # Get product info
        product_result = await session.execute(
            select(Product).where(Product.id == order.product_id)
        )
        product = product_result.scalar_one()

        payment_text = f"""
💳 اطلاعات پرداخت

📦 محصول: {product.name}
💰 مبلغ: {order.amount:,} {order.currency}

━━━━━━━━━━━━━━━━━━━━

شماره کارت:
`{settings.bank_card_number}`

به نام:
{settings.bank_account_name}

بانک:
{settings.bank_name}

━━━━━━━━━━━━━━━━━━━━

بعد از پرداخت، تصویر رسید را همینجا ارسال کنید.
"""

        await callback.message.edit_text(
            text=payment_text,
            reply_markup=PaymentInfoKeyboard.get_payment_info_keyboard(),
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_retry_payment: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)