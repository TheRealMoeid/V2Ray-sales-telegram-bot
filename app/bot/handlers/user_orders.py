"""User order history handlers."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models.order import Order, OrderStatus
from app.database.models.product import Product
from app.bot.keyboards.user_orders import UserOrdersKeyboard

logger = logging.getLogger(__name__)
router = Router(name="user_orders")


@router.callback_query(F.data == "my_orders")
async def handle_my_orders(callback: CallbackQuery, session: AsyncSession):
    """Handle user's orders button."""
    try:
        # Get user's orders
        result = await session.execute(
            select(Order)
            .where(Order.user_id == callback.from_user.id)
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        orders = result.scalars().all()
        
        if not orders:
            await callback.answer(
                "📋 شما هنوز سفارشی نداشته‌اید.",
                show_alert=True,
            )
            return
        
        # Build orders list text
        orders_text = "📋 سفارش‌های شما:\n\n"
        
        for order in orders:
            # Get product name
            product_result = await session.execute(
                select(Product).where(Product.id == order.product_id)
            )
            product = product_result.scalar_one_or_none()
            product_name = product.name if product else "نامشخص"
            
            # Status emoji
            status_emoji = {
                OrderStatus.PENDING_PAYMENT: "⏳",
                OrderStatus.RECEIPT_SUBMITTED: "📤",
                OrderStatus.APPROVED: "✅",
                OrderStatus.REJECTED: "❌",
                OrderStatus.COMPLETED: "✅",
                OrderStatus.CANCELLED: "🚫",
            }.get(order.status, "❓")
            
            orders_text += f"{status_emoji} سفارش #{order.id}\n"
            orders_text += f"   محصول: {product_name}\n"
            orders_text += f"   مبلغ: {order.amount:,} {order.currency}\n"
            orders_text += f"   وضعیت: {order.status.value}\n\n"
        
        await callback.message.edit_text(
            text=orders_text,
            reply_markup=UserOrdersKeyboard.get_orders_keyboard(orders),
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_my_orders: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("view_order:"))
async def handle_view_order(callback: CallbackQuery, session: AsyncSession):
    """Handle view order details."""
    try:
        order_id = int(callback.data.split(":")[1])
        
        # Get order and verify it belongs to user
        result = await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .where(Order.user_id == callback.from_user.id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            await callback.answer(
                "❌ سفارش یافت نشد یا متعلق به شما نیست.",
                show_alert=True,
            )
            return
        
        # Get product info
        product_result = await session.execute(
            select(Product).where(Product.id == order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        order_details = f"""
📋 جزئیات سفارش #{order.id}

📦 محصول: {product.name if product else 'نامشخص'}
💰 مبلغ: {order.amount:,} {order.currency}
📅 تاریخ: {order.created_at.strftime('%Y-%m-%d %H:%M')}

وضعیت: {order.status.value}
"""
        
        if order.status == OrderStatus.COMPLETED:
            order_details += "\n✅ این سفارش تکمیل شده است."
        elif order.status == OrderStatus.REJECTED:
            order_details += f"\n❌ این سفارش رد شده است."
        elif order.status == OrderStatus.PENDING_PAYMENT:
            order_details += "\n⏳ در انتظار پرداخت."
        elif order.status == OrderStatus.RECEIPT_SUBMITTED:
            order_details += "\n📤 رسید ارسال شده و در انتظار بررسی."
        
        await callback.message.edit_text(
            text=order_details,
            reply_markup=UserOrdersKeyboard.get_order_back_keyboard(),
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_view_order: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)
