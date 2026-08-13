"""Admin order management handlers with pagination."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
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


async def _render_orders_list(callback: CallbackQuery, session: AsyncSession, page: int, status_filter: str | None = None):
    """Helper to render paginated orders list."""
    base_query = select(Order).order_by(Order.created_at.desc())

    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            base_query = base_query.where(Order.status == status_enum)
        except ValueError:
            pass

    # Total count
    count_q = select(func.count()).select_from(Order)
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            count_q = count_q.where(Order.status == status_enum)
        except ValueError:
            pass
    total = (await session.execute(count_q)).scalar() or 0

    # Paginated fetch
    page_size = AdminOrdersKeyboard.PAGE_SIZE
    offset = (page - 1) * page_size
    result = await session.execute(
        base_query.offset(offset).limit(page_size)
    )
    orders = result.scalars().all()

    title = "🛒 سفارش‌ها"
    if status_filter:
        try:
            title = f"🛒 سفارش‌های {OrderStatus(status_filter).value}"
        except ValueError:
            pass

    text = f"{title}\nکل: {total} | صفحه {page}/{max(1, (total + page_size - 1) // page_size)}\n"

    await callback.message.edit_text(
        text=text,
        reply_markup=AdminOrdersKeyboard.get_recent_orders_keyboard(orders, page=page, total=total),
    )


@router.callback_query(F.data == "admin_orders", AdminFilter())
@router.callback_query(F.data == "admin_panel", AdminFilter())
async def handle_admin_panel_shortcut(callback: CallbackQuery, session: AsyncSession):
    """Fallback: if admin_panel callback reaches us, go to admin panel."""
    from app.bot.keyboards.admin_menu import AdminMenuKeyboard

    await callback.message.edit_text(
        text="⚙️ پنل مدیریت\n\nگزینه مورد نظر را انتخاب کنید:",
        reply_markup=AdminMenuKeyboard.get_admin_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin_orders:page:(\d+)$"), AdminFilter())
async def handle_orders_page(callback: CallbackQuery, session: AsyncSession):
    """Handle paginated orders list."""
    try:
        page = int(callback.data.split(":")[2])
        await _render_orders_list(callback, session, page=page)
        await callback.answer()
    except Exception as e:
        logger.exception(f"Error in handle_orders_page: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.regexp(r"^admin_orders:filter:([A-Z_]+):(\d+)$"), AdminFilter())
async def handle_orders_filter(callback: CallbackQuery, session: AsyncSession):
    """Handle filter by status."""
    try:
        parts = callback.data.split(":")
        status_filter = parts[2]
        page = int(parts[3])
        await _render_orders_list(callback, session, page=page, status_filter=status_filter)
        await callback.answer()
    except Exception as e:
        logger.exception(f"Error in handle_orders_filter: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    """No-op callback for disabled buttons."""
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_order:"), AdminFilter())
async def handle_admin_view_order(callback: CallbackQuery, session: AsyncSession):
    """Handle admin view order details."""
    try:
        order_id = int(callback.data.split(":")[1])
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("❌ سفارش یافت نشد.", show_alert=True)
            return

        user_result = await session.execute(
            select(User).where(User.telegram_id == order.user_id)
        )
        user = user_result.scalar_one_or_none()

        product_result = await session.execute(
            select(Product).where(Product.id == order.product_id)
        )
        product = product_result.scalar_one_or_none()

        order_details = f"""
🧾 سفارش #{order.id}

👤 **خریدار:**
{('@' + user.username) if user and user.username else (user.first_name if user else 'نامشخص')}
Telegram ID: `{order.user_id}`

📦 **محصول:** {product.name if product else 'نامشخص'}
💰 مبلغ: {order.amount:,.0f} {order.currency}
📅 تاریخ: {order.created_at.strftime('%Y-%m-%d %H:%M')}

**وضعیت:** {order.status.value}
"""

        keyboard = None
        if order.status == OrderStatus.RECEIPT_SUBMITTED:
            keyboard = AdminOrdersKeyboard.get_order_review_keyboard(order_id)
        else:
            keyboard = AdminOrdersKeyboard.get_order_back_keyboard()

        await callback.message.edit_text(text=order_details, reply_markup=keyboard, parse_mode="Markdown")
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

        result = await OrderService.approve_order_with_config_assignment(
            session=session,
            order_id=order_id,
            admin_id=admin_id,
        )

        if result is None:
            await callback.answer("❌ خطا در تأیید سفارش.", show_alert=True)
            return

        config_text, buyer_telegram_id = result

        # Send config to BUYER (Bug #4 fix)
        try:
            await callback.bot.send_message(
                chat_id=buyer_telegram_id,
                text=f"✅ پرداخت شما تأیید شد.\n\n📦 کانفیگ شما:\n\n`{config_text}`\n\n⚠️ این کانفیگ اختصاصی شماست.\n\nاز خرید شما متشکریم ❤️",
                parse_mode="Markdown",
            )
        except Exception as send_error:
            logger.exception(f"Failed to send config to user {buyer_telegram_id}: {send_error}")

        await callback.message.edit_text(
            text=f"✅ سفارش #{order_id} تأیید شد.\nکانفیگ برای مشتری ارسال شد.",
        )
        await callback.answer("✅ سفارش تأیید شد")
        logger.info(f"Order {order_id} approved by admin {admin_id}")

    except ValueError as e:
        logger.exception(f"Error approving order: {e}")
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.exception(f"Error in handle_approve_order: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.callback_query(F.data.startswith("reject_order:"), AdminFilter())
async def handle_reject_order(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle reject order - set FSM state."""
    try:
        order_id = int(callback.data.split(":")[1])
        await state.set_state(AdminStates.waiting_for_rejection_reason)
        await state.update_data(order_id=order_id)
        await callback.message.answer("لطفاً دلیل رد پرداخت را ارسال کنید:")
        await callback.answer()
    except Exception as e:
        logger.exception(f"Error in handle_reject_order: {e}")
        await callback.answer("❌ خطایی رخ داد", show_alert=True)


@router.message(AdminStates.waiting_for_rejection_reason, AdminFilter())
async def handle_rejection_reason(message: Message, state: FSMContext, session: AsyncSession):
    """Handle rejection reason text."""
    try:
        data = await state.get_data()
        order_id = data.get("order_id")
        if not order_id:
            await message.answer("❌ خطا: اطلاعات سفارش یافت نشد.")
            await state.clear()
            return

        reason = message.text.strip() if message.text else "بدون دلیل مشخص"
        admin_id = message.from_user.id

        await OrderService.reject_order(
            session=session, order_id=order_id, admin_id=admin_id, reason=reason
        )
        await session.commit()

        await message.answer(f"❌ سفارش #{order_id} رد شد.\n\nدلیل: {reason}")
        await state.clear()
        logger.info(f"Order {order_id} rejected by {admin_id}: {reason}")

    except Exception as e:
        logger.exception(f"Error in handle_rejection_reason: {e}")
        await message.answer("❌ خطایی رخ داد.")
        await state.clear()