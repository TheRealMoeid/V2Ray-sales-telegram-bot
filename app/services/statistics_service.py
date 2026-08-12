"""Statistics service."""

from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database.models.order import Order, OrderStatus
from app.database.models.user import User
from app.database.models.config import Config, ConfigStatus


class StatisticsService:
    """Service for statistics and analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_general_stats(self) -> Dict[str, int]:
        """Get general statistics."""
        # Count users
        user_result = await self.session.execute(select(func.count()).select_from(User))
        total_users = user_result.scalar() or 0

        # Count orders by status
        total_orders_result = await self.session.execute(
            select(func.count()).select_from(Order)
        )
        total_orders = total_orders_result.scalar() or 0

        pending_orders_result = await self.session.execute(
            select(func.count())
            .select_from(Order)
            .where(Order.status == OrderStatus.PENDING_PAYMENT)
        )
        pending_orders = pending_orders_result.scalar() or 0

        receipt_submitted_result = await self.session.execute(
            select(func.count())
            .select_from(Order)
            .where(Order.status == OrderStatus.RECEIPT_SUBMITTED)
        )
        receipt_submitted = receipt_submitted_result.scalar() or 0

        approved_orders_result = await self.session.execute(
            select(func.count())
            .select_from(Order)
            .where(Order.status == OrderStatus.APPROVED)
        )
        approved_orders = approved_orders_result.scalar() or 0

        completed_orders_result = await self.session.execute(
            select(func.count())
            .select_from(Order)
            .where(Order.status == OrderStatus.COMPLETED)
        )
        completed_orders = completed_orders_result.scalar() or 0

        rejected_orders_result = await self.session.execute(
            select(func.count())
            .select_from(Order)
            .where(Order.status == OrderStatus.REJECTED)
        )
        rejected_orders = rejected_orders_result.scalar() or 0

        # Count configs
        available_configs_result = await self.session.execute(
            select(func.count())
            .select_from(Config)
            .where(Config.status == ConfigStatus.AVAILABLE)
        )
        available_configs = available_configs_result.scalar() or 0

        assigned_configs_result = await self.session.execute(
            select(func.count())
            .select_from(Config)
            .where(Config.status == ConfigStatus.ASSIGNED)
        )
        assigned_configs = assigned_configs_result.scalar() or 0

        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "receipt_submitted": receipt_submitted,
            "approved_orders": approved_orders,
            "completed_orders": completed_orders,
            "rejected_orders": rejected_orders,
            "available_configs": available_configs,
            "assigned_configs": assigned_configs,
        }

    async def get_sales_stats(self) -> Dict[str, float]:
        """Get sales statistics."""
        # Total sales (completed orders)
        total_sales_result = await self.session.execute(
            select(func.sum(Order.amount)).where(Order.status == OrderStatus.COMPLETED)
        )
        total_sales = float(total_sales_result.scalar() or 0)

        # Today's sales
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_sales_result = await self.session.execute(
            select(func.sum(Order.amount)).where(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.approved_at >= today_start,
                )
            )
        )
        today_sales = float(today_sales_result.scalar() or 0)

        # This week's sales
        week_start = today_start - timedelta(days=today_start.weekday())
        week_sales_result = await self.session.execute(
            select(func.sum(Order.amount)).where(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.approved_at >= week_start,
                )
            )
        )
        week_sales = float(week_sales_result.scalar() or 0)

        # This month's sales
        month_start = today_start.replace(day=1)
        month_sales_result = await self.session.execute(
            select(func.sum(Order.amount)).where(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.approved_at >= month_start,
                )
            )
        )
        month_sales = float(month_sales_result.scalar() or 0)

        return {
            "total_sales": total_sales,
            "today_sales": today_sales,
            "week_sales": week_sales,
            "month_sales": month_sales,
        }

    async def get_full_statistics(self) -> Dict[str, Any]:
        """Get all statistics combined."""
        general_stats = await self.get_general_stats()
        sales_stats = await self.get_sales_stats()

        return {**general_stats, **sales_stats}
