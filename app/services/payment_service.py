"""Payment service."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.order import Order, OrderStatus
from app.database.models.payment_receipt import PaymentReceipt
from app.config.settings import settings


class PaymentService:
    """Service for payment-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def get_payment_info(self, amount: float, currency: str) -> str:
        """Get formatted payment information."""
        return f"""💳 اطلاعات پرداخت

مبلغ: {int(amount):,} {currency}

شماره کارت:
{settings.BANK_CARD_NUMBER}

به نام:
{settings.BANK_ACCOUNT_NAME}

بانک:
{settings.BANK_NAME}

بعد از پرداخت، تصویر رسید را همینجا ارسال کنید."""

    async def create_receipt_record(
        self,
        order_id: int,
        telegram_file_id: str,
        telegram_file_unique_id: str,
        message_id: int,
        chat_id: int,
    ) -> PaymentReceipt:
        """Create a payment receipt record."""
        receipt = PaymentReceipt(
            order_id=order_id,
            telegram_file_id=telegram_file_id,
            telegram_file_unique_id=telegram_file_unique_id,
            message_id=message_id,
            chat_id=chat_id,
        )
        self.session.add(receipt)
        await self.session.flush()
        return receipt

    async def get_receipt_for_order(self, order_id: int) -> Optional[PaymentReceipt]:
        """Get receipt for an order."""
        from sqlalchemy import select

        result = await self.session.execute(
            select(PaymentReceipt).where(PaymentReceipt.order_id == order_id)
        )
        return result.scalar_one_or_none()

    def validate_receipt_photo(self, file_size: Optional[int]) -> bool:
        """Validate receipt photo (basic validation)."""
        if file_size is None:
            return True  # Can't validate without size info

        # Max 10MB
        max_size = 10 * 1024 * 1024
        return file_size <= max_size

    @staticmethod
    async def notify_admins_new_receipt(
        session: AsyncSession,
        order: Order,
        bot,
    ) -> None:
        """Notify all admins about new receipt submission."""
        from sqlalchemy import select
        from app.database.models.user import User
        
        # Get user info
        user_result = await session.execute(
            select(User).where(User.telegram_id == order.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        # Get product info
        from app.database.models.product import Product
        product_result = await session.execute(
            select(Product).where(Product.id == order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        # Build notification message
        notification_text = f"""🧾 درخواست بررسی پرداخت

Order ID: #{order.id}

User:
@{user.username or 'نامشخص'}

User ID:
{order.user_id}

Product:
{product.name if product else 'نامشخص'}

Amount:
{order.amount:,} {order.currency}

زمان:
{order.created_at.strftime('%Y-%m-%d %H:%M')}
"""
        
        # Send to all admins
        for admin_id in settings.ADMIN_IDS:
            try:
                # Send text notification
                await bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                )
                
                # Send receipt photo if available
                if order.receipt_file_id:
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=order.receipt_file_id,
                        caption=f"📎 رسید پرداخت سفارش #{order.id}",
                    )
            except Exception as e:
                # Log error but continue with other admins
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to notify admin {admin_id}: {e}")
