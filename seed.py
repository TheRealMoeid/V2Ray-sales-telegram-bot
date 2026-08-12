#!/usr/bin/env python3
"""Seed script for development data."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database.session import init_db, async_session_maker
from app.database.models.user import User
from app.database.models.product import Product
from app.database.models.config import Config


async def seed_data():
    """Seed database with initial data."""
    
    # Initialize database tables
    await init_db()
    
    async with async_session_maker() as session:
        try:
            # Check if data already exists
            from sqlalchemy import select
            
            existing_products = await session.execute(select(Product))
            if existing_products.scalars().first():
                print("Database already seeded. Skipping...")
                return
            
            # Create admin user (placeholder - real admin ID should be set via env)
            admin_user = User(
                telegram_id=123456789,  # Placeholder - replace with real admin ID
                username="admin",
                first_name="Admin",
                is_admin=True
            )
            session.add(admin_user)
            
            # Create sample products
            products = [
                Product(
                    name="VLESS 30 Days",
                    description="High-speed VLESS configuration for 30 days",
                    price=150000,
                    currency="IRT",
                    duration_days=30,
                    protocol="VLESS",
                    is_active=True
                ),
                Product(
                    name="VLESS 90 Days",
                    description="High-speed VLESS configuration for 90 days",
                    price=400000,
                    currency="IRT",
                    duration_days=90,
                    protocol="VLESS",
                    is_active=True
                ),
                Product(
                    name="V2Ray 30 Days",
                    description="Premium V2Ray configuration for 30 days",
                    price=170000,
                    currency="IRT",
                    duration_days=30,
                    protocol="V2RAY",
                    is_active=True
                ),
            ]
            
            for product in products:
                session.add(product)
            
            await session.commit()
            
            # Refresh products to get IDs
            await session.flush()
            products_result = await session.execute(select(Product))
            products_list = products_result.scalars().all()
            
            # Create sample configs for each product
            sample_configs = []
            for product in products_list:
                for i in range(10):  # 10 configs per product
                    config = Config(
                        product_id=product.id,
                        config_text=f"vless://{product.protocol.lower()}-config-{product.id}-{i}@example.com:443?type=tcp&security=tls#Sample-{product.name}-{i}",
                        status="AVAILABLE"
                    )
                    sample_configs.append(config)
                    session.add(config)
            
            await session.commit()
            
            print(f"✅ Seeded {len(products)} products")
            print(f"✅ Seeded {len(sample_configs)} configs")
            print(f"✅ Created admin user (ID: 123456789)")
            print("\n⚠️  Remember to update the admin Telegram ID in the database!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_data())
