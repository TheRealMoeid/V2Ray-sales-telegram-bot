"""Order service."""

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.config import Config, ConfigStatus
from app.database.models.order import Order, OrderStatus
from app.database.repositories.admin_action_repository import AdminActionRepository
from app.database.repositories.config_repository import ConfigRepository
from app.database.repositories.order_repository import OrderRepository


class OrderService:
    """Service for order-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.config_repo = ConfigRepository(session)
        self.admin_action_repo = AdminActionRepository(session)

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        return await self.order_repo.get_by_id(order_id)

    async def get_user_orders(self, user_id: int) -> list[Order]:
        """Get all orders for a user."""
        return await self.order_repo.get_user_orders(user_id)

    async def get_pending_orders_for_user(self, user_id: int) -> list[Order]:
        """Get pending orders for a user."""
        return await self.order_repo.get_pending_orders_for_user(user_id)

    @staticmethod
    async def user_has_pending_order(session: AsyncSession, user_id: int) -> bool:
        """Check if user has pending order."""
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .where(
                Order.status.in_(
                    [OrderStatus.PENDING_PAYMENT, OrderStatus.RECEIPT_SUBMITTED]
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def create_order(
        session: AsyncSession,
        user_id: int,
        product_id: int,
        amount: float,
        currency: str,
        unit_price: Optional[float] = None,
    ) -> Order:
        """Create a new order."""
        if unit_price is None:
            unit_price = amount
        repo = OrderRepository(session)
        return await repo.create(
            user_id=user_id,
            product_id=product_id,
            amount=amount,
            currency=currency,
            unit_price=unit_price,
        )

    async def submit_receipt(
        self,
        order_id: int,
        receipt_file_id: str,
        receipt_file_unique_id: str,
    ) -> Optional[Order]:
        """Submit receipt for an order."""
        return await self.order_repo.submit_receipt(
            order_id=order_id,
            receipt_file_id=receipt_file_id,
            receipt_file_unique_id=receipt_file_unique_id,
        )

    @staticmethod
    async def approve_order_with_config_assignment(
        session: AsyncSession,
        order_id: int,
        admin_id: int,
    ) -> Optional[Tuple[str, int]]:
        """
        Approve an order and assign a config atomically.
        
        Returns:
            Tuple of (config_text, buyer_telegram_id) if successful, None otherwise.
            buyer_telegram_id is needed to send the config to the customer (Bug #4 fix).
        """
        async with session.begin():
            # Get the order with lock
            result = await session.execute(
                select(Order).where(Order.id == order_id).with_for_update()
            )
            order = result.scalar_one_or_none()

            if not order:
                raise ValueError("سفارش یافت نشد.")

            if order.status != OrderStatus.RECEIPT_SUBMITTED:
                raise ValueError("وضعیت سفارش برای تأیید مناسب نیست.")

            # Find an available config for this order's product
            config_result = await session.execute(
                select(Config)
                .where(Config.product_id == order.product_id)
                .where(Config.status == ConfigStatus.AVAILABLE)
                .with_for_update(skip_locked=True)
            )
            config = config_result.scalar_one_or_none()

            if not config:
                raise ValueError("کانفیگ موجود برای این محصول یافت نشد.")

            # Assign the config
            config.status = ConfigStatus.ASSIGNED
            config.assigned_to_user_id = order.user_id
            config.order_id = order.id
            config.assigned_at = datetime.utcnow()

            # Update order status
            order.status = OrderStatus.COMPLETED
            order.admin_id = admin_id
            order.approved_at = datetime.utcnow()

            await session.flush()

            # Log the admin action
            admin_action_repo = AdminActionRepository(session)
            await admin_action_repo.log_order_approval(
                admin_id=admin_id, order_id=order_id, config_id=config.id
            )

            # Return both config_text AND buyer's Telegram ID (Bug #4 fix)
            return config.config_text, order.user_id

    @staticmethod
    async def reject_order(
        session: AsyncSession,
        order_id: int,
        admin_id: int,
        reason: str,
    ) -> Optional[Order]:
        """Reject an order."""
        async with session.begin():
            result = await session.execute(
                select(Order).where(Order.id == order_id).with_for_update()
            )
            order = result.scalar_one_or_none()

            if not order:
                return None

            order.status = OrderStatus.REJECTED
            order.admin_id = admin_id
            order.rejected_at = datetime.utcnow()
            order.rejection_reason = reason

            await session.flush()

            # Log the admin action
            admin_action_repo = AdminActionRepository(session)
            await admin_action_repo.log_order_rejection(
                admin_id=admin_id, order_id=order_id, reason=reason
            )

            return order

    async def count_by_status(self, status: OrderStatus) -> int:
        """Count orders by status."""
        return await self.order_repo.count_by_status(status)

    async def count_total(self) -> int:
        """Count total orders."""
        return await self.order_repo.count_total()

    async def get_sales_sum(self) -> float:
        """Get total sales amount for completed orders."""
        return await self.order_repo.get_sales_sum()