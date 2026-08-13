"""Application configuration settings."""

import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        database_url: Optional[str] = None,
        admin_ids: Optional[str] = None,
        bank_card_number: Optional[str] = None,
        bank_account_name: Optional[str] = None,
        bank_name: Optional[str] = None,
        shop_name: Optional[str] = None,
        support_username: Optional[str] = None,
        low_stock_threshold: Optional[str] = None,
        log_level: Optional[str] = None,
    ):
        # Bot Configuration
        self.BOT_TOKEN: str = bot_token or os.getenv("BOT_TOKEN", "")

        # Database
        self.DATABASE_URL: str = database_url or os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/v2ray_bot"
        )

        # Admin IDs - handle both string (for tests) and list (for production)
        if isinstance(admin_ids, list):
            self.ADMIN_IDS: List[int] = admin_ids
        else:
            admin_ids_str = admin_ids or os.getenv("ADMIN_IDS", "")
            self.ADMIN_IDS: List[int] = [
                int(x.strip()) for x in admin_ids_str.split(",") if x.strip()
            ]

        # Bank Information
        self.BANK_CARD_NUMBER: str = bank_card_number or os.getenv("BANK_CARD_NUMBER", "")
        self.BANK_ACCOUNT_NAME: str = bank_account_name or os.getenv("BANK_ACCOUNT_NAME", "")
        self.BANK_NAME: str = bank_name or os.getenv("BANK_NAME", "")

        # Shop Configuration
        self.SHOP_NAME: str = shop_name or os.getenv("SHOP_NAME", "V2Ray Shop")
        self.SUPPORT_USERNAME: str = support_username or os.getenv("SUPPORT_USERNAME", "@support")

        # Inventory Settings
        self.LOW_STOCK_THRESHOLD: int = int(low_stock_threshold or os.getenv("LOW_STOCK_THRESHOLD", "5"))

        # Logging
        self.LOG_LEVEL: str = log_level or os.getenv("LOG_LEVEL", "INFO")
        # lowercase aliases so both settings.bot_token and settings.BOT_TOKEN work
        for _name in list(vars(self)):
            setattr(self, _name.lower(), getattr(self, _name))

    def validate(self) -> bool:
        """Validate required settings."""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        if not self.ADMIN_IDS:
            raise ValueError("At least one ADMIN_ID is required")
        return True


settings = Settings()
