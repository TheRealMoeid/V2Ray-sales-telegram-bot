"""Payment service."""

from typing import Optional
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
