"""Receipt submission handlers."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import Order, OrderStatus
from app.database.models.payment_receipt import PaymentReceipt
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)
router = Router(name="receipt")


@router.message(F.photo)
async def handle_receipt_photo(message: Message, session: AsyncSession):
    """Handle receipt photo submission."""
    try:
        # Get user's pending order (Telegram ID stored in user_id - Bug #3 already addressed)
        result = await session.execute(
            select(Order)
            .where(Order.user_id == message.from_user.id)
            .where(
                Order.status.in_(
                    [OrderStatus.PENDING_PAYMENT, OrderStatus.RECEIPT_SUBMITTED]
                )
            )
            .order_by(Order.created_at.desc())
        )
        order = result.scalar_one_or_none()

        if not order:
            await message.answer(
                "❌ ابتدا یک سفارش ایجاد کنید.",
            )
            return

        if order.status == OrderStatus.RECEIPT_SUBMITTED:
            await message.answer(
                "⚠️ رسید شما قبلاً ارسال شده و در انتظار بررسی است.",
            )
            return

        # Get photo file_id (use the highest resolution)
        photo = message.photo[-1]
        file_id = photo.file_id
        file_unique_id = photo.file_unique_id

        # Create payment receipt record
        receipt = PaymentReceipt(
            order_id=order.id,
            telegram_file_id=file_id,
            telegram_file_unique_id=file_unique_id,
            message_id=message.message_id,
            chat_id=message.chat.id,  # ✅ Bug #7 fixed
        )
        session.add(receipt)

        # Update order status
        order.status = OrderStatus.RECEIPT_SUBMITTED
        order.receipt_file_id = file_id

        await session.commit()

        # Notify admins
        await PaymentService.notify_admins_new_receipt(
            session=session,
            order=order,
            bot=message.bot,
        )

        # Send confirmation to user
        await message.answer(
            f"✅ رسید پرداخت شما دریافت شد.\n\n"
            f"📋 شماره سفارش: #{order.id}\n\n"
            f"سفارش شما در حال بررسی توسط ادمین است. پس از تأیید، کانفیگ برای شما ارسال خواهد شد."
        )

        logger.info(
            f"Receipt submitted for order {order.id} by user {message.from_user.id}"
        )

    except Exception as e:
        logger.exception(f"Error in handle_receipt_photo: {e}")
        await message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")


@router.callback_query(F.data == "send_receipt")
async def handle_send_receipt_callback(callback: CallbackQuery, session: AsyncSession):
    """Handle send receipt button callback."""
    try:
        # Check if user has pending order
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
                "❌ ابتدا یک سفارش ایجاد کنید.",
                show_alert=True,
            )
            return

        await callback.answer(
            "لطفاً تصویر رسید پرداخت را ارسال کنید.",
            show_alert=True,
        )

    except Exception as e:
        logger.exception(f"Error in handle_send_receipt_callback: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)