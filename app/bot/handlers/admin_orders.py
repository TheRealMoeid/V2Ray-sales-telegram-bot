"""Admin order management handlers."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters.admin import AdminFilter
from app.bot.keyboards.admin_orders import AdminOrdersKeyboard
from app.bot.states import AdminStates
from app.database.models.order import Order, OrderStatus
from app.database.models.product import Product
from app.database.models.user import User
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = Router(name="admin_orders")


@router.callback_query(F.data == "admin_orders", AdminFilter())
async def handle_admin_orders(callback: CallbackQuery, session: AsyncSession):
    """Handle admin orders view."""
    try:
        # Get recent orders
        result = await session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(20)
        )
        orders = result.scalars().all()

        if not orders:
            await callback.answer(
                "📋 هیچ سفارشی وجود ندارد.",
                show_alert=True,
            )
            return

        orders_text = "🛒 سفارش‌های اخیر:\n\n"

        for order in orders:
            status_emoji = {
                OrderStatus.PENDING_PAYMENT: "⏳",
                OrderStatus.RECEIPT_SUBMITTED: "📤",
                OrderStatus.APPROVED: "✅",
                OrderStatus.REJECTED: "❌",
                OrderStatus.COMPLETED: "✅",
                OrderStatus.CANCELLED: "🚫",
            }.get(order.status, "❓")

            orders_text += f"{status_emoji} #{order.id} - {order.status.value}\n"

        await callback.message.edit_text(
            text=orders_text,
            reply_markup=AdminOrdersKeyboard.get_recent_orders_keyboard(orders),
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_admin_orders: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("admin_view_order:"), AdminFilter())
async def handle_admin_view_order(callback: CallbackQuery, session: AsyncSession):
    """Handle admin view order details."""
    try:
        order_id = int(callback.data.split(":")[1])

        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer(
                "❌ سفارش یافت نشد.",
                show_alert=True,
            )
            return

        # Get user info (order.user_id is Telegram ID - Bug #3 fix)
        user_result = await session.execute(
            select(User).where(User.telegram_id == order.user_id)
        )
        user = user_result.scalar_one_or_none()

        # Get product info
        product_result = await session.execute(
            select(Product).where(Product.id == order.product_id)
        )
        product = product_result.scalar_one_or_none()

        order_details = f"""
🧾 جزئیات سفارش #{order.id}

👤 کاربر:
{user.username or user.first_name if user else 'نامشخص'}
User ID: {order.user_id}

📦 محصول: {product.name if product else 'نامشخص'}
💰 مبلغ: {order.amount:,} {order.currency}
📅 تاریخ: {order.created_at.strftime('%Y-%m-%d %H:%M')}

وضعیت: {order.status.value}
"""

        keyboard = None
        if order.status == OrderStatus.RECEIPT_SUBMITTED:
            keyboard = AdminOrdersKeyboard.get_order_review_keyboard(order_id)
        else:
            keyboard = AdminOrdersKeyboard.get_order_back_keyboard()

        await callback.message.edit_text(
            text=order_details,
            reply_markup=keyboard,
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error in handle_admin_view_order: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("approve_order:"), AdminFilter())
async def handle_approve_order(callback: CallbackQuery, session: AsyncSession):
    """Handle approve order button."""
    try:
        order_id = int(callback.data.split(":")[1])
        admin_id = callback.from_user.id

        # Approve order with transaction safety
        # approve_order_with_config_assignment now returns (config_text, buyer_telegram_id)
        result = await OrderService.approve_order_with_config_assignment(
            session=session,
            order_id=order_id,
            admin_id=admin_id,
        )

        if result is None:
            await callback.answer("❌ خطا در تأیید سفارش.", show_alert=True)
            return

        config_text, buyer_telegram_id = result

        # Send config to the BUYER (Bug #4 fix - was sending to admin before)
        try:
            await callback.bot.send_message(
                chat_id=buyer_telegram_id,  # ✅ Bug #4 fix: buyer's Telegram ID
                text=f"✅ پرداخت شما تأیید شد.\n\n📦 کانفیگ شما:\n\n`{config_text}`\n\n⚠️ این کانفیگ اختصاصی شماست.\n\nاز خرید شما متشکریم ❤️",
                parse_mode="Markdown",
            )
        except Exception as send_error:
            logger.exception(f"Failed to send config to user {buyer_telegram_id}: {send_error}")

        # Update message
        await callback.message.edit_text(
            text=f"✅ سفارش #{order_id} تأیید شد.\nکانفیگ برای مشتری ارسال شد.",
        )
        await callback.answer("✅ سفارش تأیید شد")

        logger.info(f"Order {order_id} approved by admin {admin_id}, config sent to user {buyer_telegram_id}")

    except ValueError as e:
        logger.exception(f"Error approving order {order_id}: {e}")
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.exception(f"Error in handle_approve_order: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("reject_order:"), AdminFilter())
async def handle_reject_order(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
):
    """Handle reject order button - set FSM state to wait for reason."""
    try:
        order_id = int(callback.data.split(":")[1])

        # Store order_id in FSM state
        await state.set_state(AdminStates.waiting_for_rejection_reason)
        await state.update_data(order_id=order_id)

        # Prompt admin to type the reason
        await callback.message.answer("لطفاً دلیل رد پرداخت را ارسال کنید:")
        await callback.answer()

        logger.info(f"Admin {callback.from_user.id} started rejecting order {order_id}")

    except Exception as e:
        logger.exception(f"Error in handle_reject_order: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.message(AdminStates.waiting_for_rejection_reason, AdminFilter())
async def handle_rejection_reason(
    message: Message, state: FSMContext, session: AsyncSession
):
    """Handle the rejection reason text from admin (Bug #15 fix)."""
    try:
        data = await state.get_data()
        order_id = data.get("order_id")

        if not order_id:
            await message.answer("❌ خطا: اطلاعات سفارش یافت نشد.")
            await state.clear()
            return

        reason = message.text.strip() if message.text else "بدون دلیل مشخص شده"
        admin_id = message.from_user.id

        # Reject the order with the real reason
        await OrderService.reject_order(
            session=session,
            order_id=order_id,
            admin_id=admin_id,
            reason=reason,
        )
        await session.commit()

        await message.answer(
            text=f"❌ سفارش #{order_id} رد شد.\n\nدلیل: {reason}",
        )

        await state.clear()

        logger.info(f"Order {order_id} rejected by admin {admin_id} with reason: {reason}")

    except Exception as e:
        logger.exception(f"Error in handle_rejection_reason: {e}")
        await message.answer("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
        await state.clear()