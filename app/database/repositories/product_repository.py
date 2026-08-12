"""Product repository."""

from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.product import Product


class ProductRepository:
    """Repository for Product model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, include_inactive: bool = False) -> list[Product]:
        """Get all products."""
        query = select(Product)
        if not include_inactive:
            query = query.where(Product.is_active == True)
        result = await self.session.execute(query.order_by(Product.name))
        return list(result.scalars().all())

    async def create(
        self,
        name: str,
        price: float,
        duration: int,
        description: Optional[str] = None,
        currency: str = "تومان",
        protocol: str = "VLESS",
    ) -> Product:
        """Create a new product."""
        product = Product(
            name=name,
            price=price,
            duration=duration,
            description=description,
            currency=currency,
            protocol=protocol,
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def update(
        self,
        product_id: int,
        name: Optional[str] = None,
        price: Optional[float] = None,
        duration: Optional[int] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Product]:
        """Update product fields."""
        product = await self.get_by_id(product_id)
        if not product:
            return None

        if name is not None:
            product.name = name
        if price is not None:
            product.price = price
        if duration is not None:
            product.duration = duration
        if description is not None:
            product.description = description
        if is_active is not None:
            product.is_active = is_active

        await self.session.flush()
        return product

    async def delete(self, product_id: int) -> bool:
        """Soft delete product by setting is_active to False."""
        product = await self.get_by_id(product_id)
        if not product:
            return False
        product.is_active = False
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count total active products."""
        result = await self.session.execute(
            select(Product.id).where(Product.is_active == True)
        )
        return len(result.scalars().all())
