"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = 1
    user.telegram_id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_admin = False
    return user


@pytest.fixture
def mock_admin():
    """Create a mock admin user."""
    admin = MagicMock()
    admin.id = 1
    admin.telegram_id = 123456789
    admin.username = "admin"
    admin.first_name = "Admin"
    admin.is_admin = True
    return admin


@pytest.fixture
def mock_product():
    """Create a mock product."""
    product = MagicMock()
    product.id = 1
    product.name = "VLESS 30 Days"
    product.price = 150000
    product.currency = "IRT"
    product.duration_days = 30
    product.protocol = "VLESS"
    product.is_active = True
    return product


@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = MagicMock()
    config.id = 1
    config.product_id = 1
    config.config_text = "vless://test@example.com:443"
    config.status = "AVAILABLE"
    return config


@pytest.fixture
def mock_order():
    """Create a mock order."""
    order = MagicMock()
    order.id = 1
    order.user_id = 123456789
    order.product_id = 1
    order.amount = 150000
    order.currency = "IRT"
    order.status = "PENDING_PAYMENT"
    return order
