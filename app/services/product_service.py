"""Product service."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.product_repository import ProductRepository
from app.database.models.product import Product


class ProductService:
    """Service for product-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)

    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        return await self.product_repo.get_by_id(product_id)

    async def get_active_products(self) -> List[Product]:
        """Get all active products."""
        return await self.product_repo.get_all(include_inactive=False)

    async def create_product(
        self,
        name: str,
        price: float,
        duration: int,
        description: Optional[str] = None,
        currency: str = "تومان",
        protocol: str = "VLESS",
    ) -> Product:
        """Create a new product."""
        return await self.product_repo.create(
            name=name,
            price=price,
            duration=duration,
            description=description,
            currency=currency,
            protocol=protocol,
        )

    async def update_product(
        self,
        product_id: int,
        name: Optional[str] = None,
        price: Optional[float] = None,
        duration: Optional[int] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Product]:
        """Update product fields."""
        return await self.product_repo.update(
            product_id=product_id,
            name=name,
            price=price,
            duration=duration,
            description=description,
            is_active=is_active,
        )

    async def deactivate_product(self, product_id: int) -> bool:
        """Soft delete product by setting is_active to False."""
        return await self.product_repo.delete(product_id)

    async def count_products(self) -> int:
        """Count total active products."""
        return await self.product_repo.count()
