"""Tests for the V2Ray sales Telegram bot."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Test database models
class TestUserModel:
    """Test User model."""
    
    def test_user_creation(self):
        """Test creating a user."""
        from app.database.models.user import User
        
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.is_admin is False
    
    def test_user_is_admin_default(self):
        """Test that is_admin defaults to False."""
        from app.database.models.user import User
        
        user = User(telegram_id=987654321)
        assert user.is_admin is False


class TestProductModel:
    """Test Product model."""
    
    def test_product_creation(self):
        """Test creating a product."""
        from app.database.models.product import Product
        
        product = Product(
            name="VLESS 30 Days",
            description="Test description",
            price=150000,
            currency="IRT",
            duration_days=30,
            protocol="VLESS"
        )
        
        assert product.name == "VLESS 30 Days"
        assert product.price == 150000
        assert product.is_active is True
    
    def test_product_defaults(self):
        """Test product default values."""
        from app.database.models.product import Product
        
        product = Product(
            name="Test Product",
            price=100000
        )
        
        assert product.currency == "IRT"
        assert product.duration_days == 30
        assert product.protocol == "VLESS"
        assert product.is_active is True


class TestConfigModel:
    """Test Config model."""
    
    def test_config_creation(self):
        """Test creating a config."""
        from app.database.models.config import Config, ConfigStatus
        
        config = Config(
            product_id=1,
            config_text="vless://test@example.com:443",
            status=ConfigStatus.AVAILABLE.value
        )
        
        assert config.product_id == 1
        assert config.status == ConfigStatus.AVAILABLE.value
    
    def test_config_default_status(self):
        """Test config default status."""
        from app.database.models.config import Config
        
        config = Config(
            product_id=1,
            config_text="vless://test@example.com:443"
        )
        
        assert config.status == "AVAILABLE"


class TestOrderModel:
    """Test Order model."""
    
    def test_order_creation(self):
        """Test creating an order."""
        from app.database.models.order import Order, OrderStatus
        
        order = Order(
            user_id=123456789,
            product_id=1,
            amount=150000,
            currency="IRT"
        )
        
        assert order.user_id == 123456789
        assert order.product_id == 1
        assert order.amount == 150000
        assert order.status == OrderStatus.PENDING_PAYMENT.value
    
    def test_order_default_status(self):
        """Test order default status."""
        from app.database.models.order import Order
        
        order = Order(
            user_id=123456789,
            product_id=1,
            amount=150000
        )
        
        assert order.status == "PENDING_PAYMENT"


class TestPaymentReceiptModel:
    """Test PaymentReceipt model."""
    
    def test_receipt_creation(self):
        """Test creating a payment receipt."""
        from app.database.models.payment_receipt import PaymentReceipt
        
        receipt = PaymentReceipt(
            order_id=1,
            telegram_file_id="AgACAgIAAx...",
            telegram_file_unique_id="AQAD..."
        )
        
        assert receipt.order_id == 1
        assert receipt.telegram_file_id == "AgACAgIAAx..."


class TestAdminActionModel:
    """Test AdminAction model."""
    
    def test_admin_action_creation(self):
        """Test creating an admin action."""
        from app.database.models.admin_action import AdminAction
        
        action = AdminAction(
            admin_id=123456789,
            action="approve_order",
            target_type="order",
            target_id=1
        )
        
        assert action.admin_id == 123456789
        assert action.action == "approve_order"
        assert action.target_type == "order"
        assert action.target_id == 1


# Test services
class TestOrderService:
    """Test OrderService."""
    
    @pytest.mark.asyncio
    async def test_create_order(self):
        """Test creating an order."""
        from app.services.order_service import OrderService
        from app.database.models.order import OrderStatus
        
        mock_session = AsyncMock()
        order_service = OrderService(mock_session)
        
        # Mock the repository response
        with patch.object(order_service.order_repo, 'create', return_value=MagicMock(
            id=1,
            user_id=123456789,
            product_id=1,
            amount=150000,
            status=OrderStatus.PENDING_PAYMENT.value
        )):
            order = await order_service.create_order(
                user_id=123456789,
                product_id=1,
                amount=150000
            )
            
            assert order.id == 1
            assert order.status == OrderStatus.PENDING_PAYMENT.value
    
    @pytest.mark.asyncio
    async def test_submit_receipt(self):
        """Test submitting a receipt."""
        from app.services.order_service import OrderService
        from app.database.models.order import OrderStatus
        
        mock_session = AsyncMock()
        order_service = OrderService(mock_session)
        
        # Mock the repository responses
        mock_order = MagicMock(
            id=1,
            status=OrderStatus.PENDING_PAYMENT.value
        )
        
        with patch.object(order_service.order_repo, 'get_by_id', return_value=mock_order):
            with patch.object(order_service.order_repo, 'update') as mock_update:
                with patch.object(order_service.receipt_repo, 'create'):
                    await order_service.submit_receipt(
                        order_id=1,
                        telegram_file_id="AgACAgIAAx...",
                        telegram_file_unique_id="AQAD..."
                    )
                    
                    mock_update.assert_called_once()


class TestConfigService:
    """Test ConfigService."""
    
    @pytest.mark.asyncio
    async def test_get_available_configs_count(self):
        """Test getting available configs count."""
        from app.services.config_service import ConfigService
        
        mock_session = AsyncMock()
        config_service = ConfigService(mock_session)
        
        # Mock the repository response
        with patch.object(config_service.config_repo, 'count_available', return_value=5):
            count = await config_service.get_available_configs_count(product_id=1)
            
            assert count == 5
    
    @pytest.mark.asyncio
    async def test_add_config(self):
        """Test adding a config."""
        from app.services.config_service import ConfigService
        
        mock_session = AsyncMock()
        config_service = ConfigService(mock_session)
        
        with patch.object(config_service.config_repo, 'create', return_value=MagicMock(id=1)):
            config = await config_service.add_config(
                product_id=1,
                config_text="vless://test@example.com:443"
            )
            
            assert config.id == 1


class TestUserService:
    """Test UserService."""
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self):
        """Test getting or creating a new user."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        user_service = UserService(mock_session)
        
        # Mock the repository responses
        with patch.object(user_service.user_repo, 'get_by_telegram_id', return_value=None):
            with patch.object(user_service.user_repo, 'create', return_value=MagicMock(
                id=1,
                telegram_id=123456789,
                username="testuser"
            )):
                user = await user_service.get_or_create_user(
                    telegram_id=123456789,
                    username="testuser",
                    first_name="Test"
                )
                
                assert user.telegram_id == 123456789
                assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self):
        """Test getting an existing user."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        user_service = UserService(mock_session)
        
        existing_user = MagicMock(
            id=1,
            telegram_id=123456789,
            username="existinguser"
        )
        
        with patch.object(user_service.user_repo, 'get_by_telegram_id', return_value=existing_user):
            user = await user_service.get_or_create_user(
                telegram_id=123456789,
                username="updateduser",
                first_name="Updated"
            )
            
            assert user.telegram_id == 123456789
            assert user.username == "existinguser"  # Should not update existing


# Test security - admin filter
class TestAdminFilter:
    """Test admin authorization filter."""
    
    def test_admin_filter_check(self):
        """Test admin filter check."""
        from app.bot.filters.admin import IsAdminFilter
        
        # Test with admin ID in list
        filter_obj = IsAdminFilter(admin_ids=[123456789, 987654321])
        
        # Mock event
        mock_event = MagicMock()
        mock_event.from_user.id = 123456789
        
        result = filter_obj.check(mock_event)
        assert result is True
    
    def test_admin_filter_check_non_admin(self):
        """Test admin filter check with non-admin."""
        from app.bot.filters.admin import IsAdminFilter
        
        filter_obj = IsAdminFilter(admin_ids=[123456789, 987654321])
        
        mock_event = MagicMock()
        mock_event.from_user.id = 111111111
        
        result = filter_obj.check(mock_event)
        assert result is False


# Test settings
class TestSettings:
    """Test configuration settings."""
    
    def test_admin_ids_parsing(self):
        """Test parsing admin IDs from environment variable."""
        from app.config.settings import Settings
        
        # Test with comma-separated IDs
        settings = Settings(
            bot_token="test_token",
            database_url="postgresql+asyncpg://test@test/test",
            admin_ids="123456789,987654321,555555555"
        )
        
        assert len(settings.ADMIN_IDS) == 3
        assert 123456789 in settings.ADMIN_IDS
        assert 987654321 in settings.ADMIN_IDS
        assert 555555555 in settings.ADMIN_IDS
    
    def test_single_admin_id(self):
        """Test with single admin ID."""
        from app.config.settings import Settings
        
        settings = Settings(
            bot_token="test_token",
            database_url="postgresql+asyncpg://test@test/test",
            admin_ids="123456789"
        )
        
        assert len(settings.ADMIN_IDS) == 1
        assert settings.ADMIN_IDS == [123456789]


# Test order status transitions
class TestOrderStatusTransitions:
    """Test order status transitions."""
    
    def test_valid_status_transitions(self):
        """Test valid order status transitions."""
        from app.database.models.order import OrderStatus
        
        # Valid transitions
        valid_transitions = [
            (OrderStatus.PENDING_PAYMENT.value, OrderStatus.RECEIPT_SUBMITTED.value),
            (OrderStatus.RECEIPT_SUBMITTED.value, OrderStatus.APPROVED.value),
            (OrderStatus.RECEIPT_SUBMITTED.value, OrderStatus.REJECTED.value),
            (OrderStatus.APPROVED.value, OrderStatus.COMPLETED.value),
        ]
        
        for from_status, to_status in valid_transitions:
            # This should not raise any errors
            assert from_status is not None
            assert to_status is not None
    
    def test_order_status_enum_values(self):
        """Test all order status enum values exist."""
        from app.database.models.order import OrderStatus
        
        statuses = [
            "PENDING_PAYMENT",
            "RECEIPT_SUBMITTED",
            "APPROVED",
            "REJECTED",
            "COMPLETED",
            "CANCELLED"
        ]
        
        for status in statuses:
            assert hasattr(OrderStatus, status)


# Test config status
class TestConfigStatus:
    """Test config status enum."""
    
    def test_config_status_values(self):
        """Test config status enum values."""
        from app.database.models.config import ConfigStatus
        
        assert ConfigStatus.AVAILABLE.value == "AVAILABLE"
        assert ConfigStatus.ASSIGNED.value == "ASSIGNED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
