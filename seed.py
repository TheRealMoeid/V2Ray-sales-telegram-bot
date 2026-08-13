#!/usr/bin/env python3
"""Seed script for development data - robust version."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, inspect

from app.config.settings import settings
from app.database.models.config import Config
from app.database.models.product import Product
from app.database.models.user import User
from app.database.session import async_session_maker, init_db


def get_real_admin_id() -> int:
    """Get the real admin ID from settings, fail if not configured."""
    admin_ids_raw = getattr(settings, "ADMIN_IDS", None) or getattr(
        settings, "admin_ids", None
    )

    if not admin_ids_raw:
        print("❌ Error: ADMIN_IDS environment variable is not set.")
        print("   Please set ADMIN_IDS in your .env file before running seed.")
        print("   Example: ADMIN_IDS=123456789,987654321")
        sys.exit(1)

    try:
        first_admin_id = int(str(admin_ids_raw).split(",")[0].strip())
        return first_admin_id
    except (ValueError, IndexError) as e:
        print(f"❌ Error: Invalid ADMIN_IDS format: {admin_ids_raw}")
        print(f"   Details: {e}")
        sys.exit(1)


def get_model_columns(model_class):
    """Get valid column names for a SQLAlchemy model."""
    try:
        mapper = inspect(model_class)
        return {column.key for column in mapper.columns}
    except Exception:
        return set()


def safe_create(model_class, **kwargs):
    """Create a model instance, filtering invalid fields and applying fallbacks."""
    valid = get_model_columns(model_class)
    filtered = {}
    skipped = []

    # Fallbacks: map common alternative names to each other
    FALLBACKS = {
        "duration_days": ["duration", "duration_in_days", "validity_days", "days"],
        "duration": ["duration_days", "duration_in_days", "validity_days", "days"],
        "is_active": ["active", "enabled"],
        "active": ["is_active", "enabled"],
        "telegram_id": ["tg_id", "user_id"],
        "username": ["user_name"],
    }

    for key, value in kwargs.items():
        if key in valid:
            filtered[key] = value
        elif key in FALLBACKS:
            # Try each fallback name
            matched = False
            for alt in FALLBACKS[key]:
                if alt in valid:
                    filtered[alt] = value
                    matched = True
                    break
            if not matched:
                skipped.append(key)
        else:
            # Unknown field - skip with warning
            skipped.append(key)

    if skipped:
        print(f"⚠️  Skipped fields for {model_class.__name__}: {skipped}")
        print(f"   Valid columns: {sorted(valid)}")

    return model_class(**filtered)


async def seed_data():
    """Seed database with initial data."""
    await init_db()

    # Get admin ID from settings (fails if not configured - Bug #23 fix)
    real_admin_id = get_real_admin_id()

    async with async_session_maker() as session:
        try:
            # Check if data already exists
            existing_products = await session.execute(select(Product))
            if existing_products.scalars().first():
                print("Database already seeded. Skipping...")
                return

            # Create admin user
            admin_user = safe_create(
                User,
                telegram_id=real_admin_id,
                username="therealMoeid",
                first_name="Moeid",
                last_name=None,
            )
            session.add(admin_user)

            # Create sample products
            products_data = [
                {
                    "name": "VLESS 30 Days",
                    "description": "High-speed VLESS configuration for 30 days",
                    "price": 150000,
                    "currency": "IRT",
                    "duration_days": 30,
                    "protocol": "VLESS",
                    "is_active": True,
                },
                {
                    "name": "VLESS 90 Days",
                    "description": "High-speed VLESS configuration for 90 days",
                    "price": 400000,
                    "currency": "IRT",
                    "duration_days": 90,
                    "protocol": "VLESS",
                    "is_active": True,
                },
                {
                    "name": "V2Ray 30 Days",
                    "description": "Premium V2Ray configuration for 30 days",
                    "price": 170000,
                    "currency": "IRT",
                    "duration_days": 30,
                    "protocol": "V2RAY",
                    "is_active": True,
                },
            ]

            products = []
            for data in products_data:
                p = safe_create(Product, **data)
                products.append(p)
                session.add(p)

            await session.commit()
            await session.flush()

            # Re-fetch to get IDs
            result = await session.execute(select(Product))
            products_list = result.scalars().all()

            # Create sample configs for each product
            sample_configs = []
            for product in products_list:
                for i in range(10):
                    cfg_kwargs = {
                        "product_id": product.id,
                        "config_text": f"vless://{product.name.lower().replace(' ', '-')}-{i}@example.com:443?type=tcp&security=tls#Sample-{product.name}-{i}",
                        "status": "AVAILABLE",
                    }
                    config = safe_create(Config, **cfg_kwargs)
                    sample_configs.append(config)
                    session.add(config)

            await session.commit()

            print(f"✅ Seeded {len(products)} products")
            print(f"✅ Seeded {len(sample_configs)} configs")
            print(f"✅ Created admin user (Telegram ID: {real_admin_id})")
            print(f"\n🎉 Go to Telegram and run /start on @Moeid_TestBot")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding database: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(seed_data())