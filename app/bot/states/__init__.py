"""Bot states package."""

from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """User FSM states."""

    waiting_for_product_selection = State()
    waiting_for_receipt = State()


class AdminStates(StatesGroup):
    """Admin FSM states."""

    # Product management
    waiting_for_product_name = State()
    waiting_for_product_price = State()
    waiting_for_product_duration = State()
    waiting_for_product_description = State()

    # Config management
    waiting_for_config = State()
    waiting_for_config_product_selection = State()

    # Reject order
    waiting_for_rejection_reason = State()

    # Add product workflow
    creating_product = State()
