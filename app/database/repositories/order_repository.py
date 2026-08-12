"""Order repository."""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.order import Order, OrderStatus


class OrderRepository:
    """Repository for Order model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(self, order_id: int) -> Optional[Order]:
        """Get order by ID with row lock for atomic operations."""
        stmt = select(Order).where(Order.id == order_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_orders(self, user_id: int) -> list[Order]:
        """Get all orders for a user."""
        result = await self.session.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_orders_for_user(
        self, user_id: int
    ) -> list[Order]:
        """Get pending orders for a user."""
        result = await self.session.execute(
            select(Order).where(
                and_(
                    Order.user_id == user_id,
                    Order.status.in_(
                        [OrderStatus.PENDING_PAYMENT, OrderStatus.RECEIPT_SUBMITTED]
                    ),
                )
            )
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_id: int,
        product_id: int,
        amount: float,
        currency: str,
        unit_price: float,
    ) -> Order:
        """Create a new order."""
        order = Order(
            user_id=user_id,
            product_id=product_id,
            amount=amount,
            currency=currency,
            unit_price=unit_price,
            status=OrderStatus.PENDING_PAYMENT,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def update_status(
        self, order_id: int, status: OrderStatus, admin_id: Optional[int] = None
    ) -> Optional[Order]:
        """Update order status."""
        order = await self.get_by_id(order_id)
        if not order:
            return None

        order.status = status
        if admin_id is not None:
            order.admin_id = admin_id

        await self.session.flush()
        return order

    async def submit_receipt(
        self,
        order_id: int,
        receipt_file_id: str,
        receipt_file_unique_id: str,
    ) -> Optional[Order]:
        """Submit receipt for an order."""
        order = await self.get_by_id(order_id)
        if not order:
            return None

        order.status = OrderStatus.RECEIPT_SUBMITTED
        order.receipt_file_id = receipt_file_id
        order.receipt_file_unique_id = receipt_file_unique_id

        await self.session.flush()
        return order

    async def approve_order(
        self, order_id: int, admin_id: int
    ) -> tuple[Optional[Order], str]:
        """
        Approve an order atomically.
        Returns (order, error_message).
        Error message is empty if successful.
        """
        # Lock the order
        order = await self.get_by_id_with_lock(order_id)
        if not order:
            return None, "Order not found"

        if order.status != OrderStatus.RECEIPT_SUBMITTED:
            return order, f"Order is not in RECEIPT_SUBMITTED status (current: {order.status})"

        if order.status == OrderStatus.APPROVED or order.status == OrderStatus.COMPLETED:
            return order, "Order already approved"

        order.status = OrderStatus.APPROVED
        order.admin_id = admin_id
        order.approved_at = datetime.utcnow()

        await self.session.flush()
        return order, ""

    async def reject_order(
        self, order_id: int, admin_id: int, reason: str
    ) -> Optional[Order]:
        """Reject an order."""
        order = await self.get_by_id(order_id)
        if not order:
            return None

        order.status = OrderStatus.REJECTED
        order.admin_id = admin_id
        order.rejection_reason = reason
        order.rejected_at = datetime.utcnow()

        await self.session.flush()
        return order

    async def complete_order(self, order_id: int) -> Optional[Order]:
        """Mark order as completed after config delivery."""
        order = await self.get_by_id(order_id)
        if not order:
            return None

        order.status = OrderStatus.COMPLETED
        await self.session.flush()
        return order

    async def count_by_status(self, status: OrderStatus) -> int:
        """Count orders by status."""
        result = await self.session.execute(
            select(func.count()).select_from(Order).where(Order.status == status)
        )
        return result.scalar() or 0

    async def count_total(self) -> int:
        """Count total orders."""
        result = await self.session.execute(select(func.count()).select_from(Order))
        return result.scalar() or 0

    async def get_sales_sum(self) -> float:
        """Get total sales amount for completed orders."""
        result = await self.session.execute(
            select(func.sum(Order.amount)).where(Order.status == OrderStatus.COMPLETED)
        )
        return float(result.scalar() or 0)
