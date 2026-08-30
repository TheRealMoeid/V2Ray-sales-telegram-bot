# Known Issues — V2Ray Sales Telegram Bot

This file replaces the numbered bug lists in `(DONE)V2Ray_Bot_Code_Review.md` and
`BUGS.md`. Those two documents were point-in-time audits of earlier, broken states
of the repository — almost everything they flagged has since been fixed. This file
keeps only the items from those reports that are **still true against the current
code**, plus one newly-discovered regression.

Those two files should be moved to a `docs/history/` folder (or deleted) once this
file is in place, so nobody mistakes a resolved historical bug for a live one.

---

## 🔴 New — Admin "Users" screen crashes (regression, previously undocumented)

**File:** `app/bot/handlers/admin_statistics.py`, `handle_admin_users`

```python
users_text = ""
users_text += f"• {_escape_markdown(name)} (ID: `{user.telegram_id}`)\n"
users_text += "**۱۰ کاربر اخیر:**\n"

if recent_users:
    for user in recent_users:
        name = f"@{user.username}" if user.username else (user.first_name or "بدون نام")
        users_text += f"• {_escape_markdown(name)} (ID: `{user.telegram_id}`)\n"
```

The second line references `name` and `user` before either is ever assigned — both
are only defined inside the `for` loop several lines later. This raises
`NameError: name 'name' is not defined` every time this handler runs, regardless of
whether any users exist. The "👥 کاربران" (Users) admin screen is currently
**completely broken**.

**Fix:** delete the two stray lines above the `if recent_users:` block; the header
text (`"**۱۰ کاربر اخیر:**\n"`) should be set once, before the loop, and the
per-user line should only be built inside the loop where `user`/`name` exist.

---

## 🟡 Alembic migration is still out of sync with the models (schema drift)

**File:** `alembic/versions/001_initial_migration.py` vs. `app/database/models/*`

Confirmed still true by diffing the migration against current model definitions:

| Table | Migration says | Model says | Impact |
|---|---|---|---|
| `products` | column `duration_days` | attribute `duration` | `UndefinedColumn` if migration is applied |
| `products` | `price` = `Integer` | `price` = `Numeric(10,2)` | type mismatch / precision loss |
| `orders` | no `unit_price` column | `unit_price` required (`nullable=False`) | every order insert fails |
| `orders` | no `receipt_file_unique_id` column | model has it | drift |
| `configs` | `status` = `String(20)` | `status` = native `Enum(ConfigStatus)` | type mismatch |
| `payment_receipts` | no `chat_id` column | `chat_id` required (`nullable=False`) | receipt insert fails |
| `payment_receipts` | `message_id` nullable | model requires it | drift |
| `users` | has `is_admin` column | model has no such column (only a hardcoded property) | dead column if applied |

**Why it still matters:** `app/database/session.py`'s `init_db()` runs
`Base.metadata.create_all()` on every startup, which currently masks this drift in
practice (the live schema always matches the ORM because it's generated from the
ORM, not from Alembic). But the Dockerfile/README both document `alembic upgrade
head` as the supported migration path — running that against a genuinely fresh
database would produce a schema the app cannot use.

**Fix:** regenerate the migration from current models
(`alembic revision --autogenerate -m "sync with models"`), or explicitly document
that `create_all()` is the source of truth for now and Alembic is not yet
production-ready.

---

## 🟡 Dead code

None of these cause bugs today, but they're maintenance traps — a future
contributor may assume they're the "real" implementation and update them instead
of the code paths actually in use.

- **`OrderRepository.approve_order()`** (`app/database/repositories/order_repository.py`)
  — a fully-written, unused approve method with logic that has already diverged
  from the real approval path (`OrderService.approve_order_with_config_assignment`,
  which is what handlers actually call). Delete it, or have the service delegate
  to it for a single source of truth.
- **`ProductService` / `ProductRepository`** (`app/services/product_service.py`,
  `app/database/repositories/product_repository.py`) — fully implemented, never
  called from any handler. There is currently no admin UI for creating or editing
  products; that only happens via `seed.py` or direct DB access.
- **`PaymentService.get_payment_info()`** and **`PaymentService.validate_receipt_photo()`**
  (`app/services/payment_service.py`) — never called. `purchase.py` builds payment
  text inline instead of using `get_payment_info()` (duplicated, slightly
  different formatting), and `receipt.py` never validates receipt photo file size
  before accepting it.
- **`ProductListKeyboard.get_product_confirmation()`** and its
  `confirm_product:` / `cancel_order` callbacks — never wired to any handler. The
  live purchase flow goes straight from `select_product:` to order creation with
  no confirmation step.
- **Duplicate `admin_panel` callback handler** — both `admin_commands.py`
  (`handle_admin_panel_callback`) and `admin_orders.py`
  (`handle_admin_panel_shortcut`) register a handler for
  `F.data == "admin_panel"`. Since `admin_commands_router` is included first in
  `app/main.py`, the copy in `admin_orders.py` is permanently shadowed and never
  fires. Harmless today, but confusing — remove the shadowed one.

---

## 🟢 Minor / cosmetic

- **`Numeric` columns typed as `float` in Python** (`product.py`, `order.py`:
  `price`, `amount`, `unit_price`). SQLAlchemy's `Numeric` returns
  `decimal.Decimal` by default, not `float`, so the type hints are inaccurate.
  Not currently causing failures (the code only formats these for display), but a
  foot-gun if arithmetic mixing `Decimal` and `float` is added later. Either add
  `asdecimal=False` to the columns or change the type hints to `Decimal`.
- **Test count drift**: README states "23 tests in `tests/test_bot.py`"; the
  current file contains ~24 test methods. Minor, but worth re-counting whenever
  the suite changes.
- **Mock-only test suite**: `tests/test_bot.py` uses `AsyncMock`/`MagicMock`
  throughout and never exercises a real (or in-memory) database or the full
  handler call chain. It would **not** have caught most of the bugs described in
  the historical reports, nor would it catch the `admin_statistics.py` regression
  above. Worth adding at least one integration test against SQLite/async engine
  that runs the purchase → receipt → approve flow end-to-end.

---

## Resolved (for reference only — no action needed)

Everything else previously listed in `(DONE)V2Ray_Bot_Code_Review.md` (Bugs
#1–13, #15–17, #20, #23) and `BUGS.md` (Bugs #1–7) has been verified as fixed in
the current codebase, including:

- The two startup-blocking syntax/import errors.
- The `Order.user_id` foreign-key mismatch (now stores Telegram ID directly, no
  FK — documented in code as "Bug #3 fix").
- Config sent to the wrong chat on approval (now sent to the buyer's Telegram
  ID).
- Missing `Config`/`ConfigStatus` and `datetime` imports in `order_service.py`.
- Missing `PaymentReceipt.chat_id`.
- `edit_text` + `ReplyKeyboardMarkup` crash on "back to menu".
- `ConfigService.get_all_products()` missing `session` argument.
- Nonexistent `StatisticsService` method names.
- `ProductListKeyboard` method-name mismatch.
- `ScalarResult.count()` misuse.
- `AdminActionRepository.create()` silently dropping metadata.
- Ignored/hardcoded rejection reasons (FSM now wired up correctly).
- Catch-all admin text handler intercepting non-config messages (now gated by
  FSM state).
- Duplicate welcome message / duplicate menu edit.
- Config-to-product association being discarded (now stored via
  `state.update_data`).
- Hardcoded fallback admin Telegram ID in `seed.py`.
- Broken pagination beyond page 1 in the admin orders list.
- Admins being able to delete already-assigned configs.
- `receipt_file_unique_id` always being `NULL`.
- Crash in `notify_admins_new_receipt` when no `User` row exists yet.
- `submitted_orders` vs. `receipt_submitted` stats key mismatch.
- Inconsistent `parse_mode` in `purchase.py`.
- Stale user profile info never being refreshed on repeat visits.

If any of the above resurfaces, treat it as a regression, not a known issue.
