### Critical Bugs (Will Crash the Bot)

**1. Undefined Variables in `admin_statistics.py`**
In `app/bot/handlers/admin_statistics.py`, the `handle_admin_users` function contains a syntax/logic error that will cause a `NameError` immediately when an admin tries to view users.
```python
        # BUG: 'name' and 'user' are not defined yet!
        users_text = ""
        users_text += f"• {_escape_markdown(name)} (ID: `{user.telegram_id}`)\n" 
        users_text += "**۱۰ کاربر اخیر:**\n"

        if recent_users:
            for user in recent_users:
                name = ...
```
**Fix:** Remove the two lines before the `if recent_users:` block.
```python
        users_text = "**۱۰ کاربر اخیر:**\n"
        if recent_users:
            for user in recent_users:
                name = f"@{user.username}" if user.username else (user.first_name or "بدون نام")
                users_text += f"• {_escape_markdown(name)} (ID: `{user.telegram_id}`)\n"
```

**2. Database Column Mismatch (`duration` vs `duration_days`)**
In `app/database/models/product.py`, the model defines `duration`:
```python
duration: Mapped[int] = mapped_column(Integer, default=30)
```
However, the Alembic migration (`001_initial_migration.py`) creates the column as `duration_days`. SQLAlchemy will look for a column named `duration` in the database, which does not exist. Any read/write operation on the `Product` model will result in a `ProgrammingError`.
**Fix:** Explicitly map the column name in the model:
```python
duration: Mapped[int] = mapped_column("duration_days", Integer, default=30)
```

### High Severity Bugs (Logic & Data Integrity)

**3. Missing Auto-Commit in Database Middleware**
The `DatabaseSessionMiddleware` in `app/bot/middlewares/database.py` provides a session but **does not automatically commit or rollback** transactions. It relies entirely on every individual handler to manually call `await session.commit()`. If a handler forgets, data will silently fail to save.
**Fix:** Update the middleware to manage transactions automatically:
```python
class DatabaseSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: Update, data: dict[str, Any]) -> Any:
        async with async_session() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.commit()
```

**4. Receipt Photo Interception**
In `app/bot/handlers/receipt.py`, the handler `@router.message(F.photo)` intercepts **all** photos sent to the bot, regardless of the user's state. If an admin accidentally sends a photo while adding configs, or a user sends a photo for support, it will attempt to process it as a receipt.
**Fix:** Gate the handler with a state filter so it only triggers when the user is supposed to be sending a receipt (e.g., `@router.message(UserStates.waiting_for_receipt, F.photo)`).

**5. Duplicate Callback Registrations**
Both `admin_commands.py` and `admin_orders.py` register a handler for `F.data == "admin_panel"`. Aiogram will only execute the first one it encounters, making the other dead code. Ensure only one router handles this callback.

### Minor Issues & Code Quality

**6. Order Status Inconsistency**
`OrderService.approve_order_with_config_assignment` sets the order status directly to `COMPLETED`. However, `OrderRepository.approve_order` sets it to `APPROVED`. This inconsistency suggests a confused workflow; `OrderRepository.approve_order` appears to be dead code if the service is the one being called.

**7. Naive Datetime Usage**
The code uses `datetime.utcnow()` throughout `order_service.py` and `statistics_service.py`. This returns a naive datetime object, which can cause warnings or bugs with timezone-aware database columns. Use `datetime.now(timezone.utc)` instead.

**8. Strict Config Validation**
In `admin_config.py`, `handle_config_text_submission` checks if the text starts with `"vless://"`. If the admin copies a valid config with leading whitespace, it will fail. Add `.strip()` to the validation logic.

**9. Missing Total Users Display**
In `handle_admin_users`, the `total_users` variable is queried from the database but never added to the `users_text` output string, so the admin never sees the total count.
