# V2Ray Sales Telegram Bot

A Telegram bot for selling V2Ray/VLESS configuration subscriptions, built with **aiogram 3**, **SQLAlchemy 2 (async)**, and **PostgreSQL**. Customers browse products, pay by bank transfer, upload a receipt photo, and receive their config automatically once an admin approves the payment. The whole flow, including bot text, is in Persian.

## What it does

The bot models a small manual storefront: an admin stocks pre-generated VLESS/VMess/Trojan config strings against products, customers buy a product and pay by card-to-card transfer, and an admin reviews the payment receipt before the config is released. There is no payment gateway integration; approval is a human step.

**Customer flow**
1. `/start` registers the user and shows the main menu.
2. "خرید کانفیگ" (Buy config) lists active products with available stock.
3. Selecting a product creates a `PENDING_PAYMENT` order and shows bank transfer details (card number, account name, bank name).
4. The customer sends a photo of the payment receipt, which flips the order to `RECEIPT_SUBMITTED` and notifies every admin (as text plus the receipt photo).
5. An admin approves or rejects. On approval, the bot atomically assigns an `AVAILABLE` config to the order, marks it `COMPLETED`, and DMs the config string straight to the buyer. On rejection, the admin is prompted for a reason via FSM, which is stored and shown to the customer.
6. Customers can only have one order in flight at a time; a second purchase attempt is blocked until the current one resolves.

**Admin flow**
Admins (identified by Telegram ID via an `AdminFilter`, not a DB flag) get an inline panel to:
- Review and paginate orders, optionally filtered by status
- Approve/reject pending receipts
- Add new configs (validated to start with `vless://`, `vmess://`, or `trojan://`) against a chosen product, or delete unassigned ones
- View shop statistics: user count, order counts by status, total/today/week/month sales, and available vs. assigned config counts
- Browse the 10 most recently registered users

## Tech stack

| Layer | Choice |
|---|---|
| Bot framework | [aiogram 3](https://docs.aiogram.dev/) (async, router-based, FSM for multi-step admin flows) |
| Database | PostgreSQL, accessed via SQLAlchemy 2.0 async ORM and `asyncpg` |
| Migrations | Alembic |
| Config | Environment variables via `python-dotenv`, loaded into a `Settings` object |
| Testing | `pytest` + `pytest-asyncio` (23 tests in `tests/test_bot.py`) |
| Packaging | `requirements.txt` and `pyproject.toml` (Python ≥ 3.12) |
| Deployment | Dockerfile (non-root user) + `docker-compose.yml` (bot + Postgres, with healthcheck-gated startup) |

## Project layout

```
app/
  main.py                  # Bot/Dispatcher setup, router + middleware registration, polling loop
  config/
    settings.py             # Settings loaded from env vars (bot token, DB URL, admin IDs, bank info, shop info)
  database/
    session.py               # Async engine, session maker, init_db()/close_db()
    models/
      user.py                # User (Telegram identity)
      product.py              # Product (name, price, duration, protocol, active flag)
      config.py                # Config (a single VLESS/VMess/Trojan string, AVAILABLE/ASSIGNED)
      order.py                  # Order (status machine, amount, receipt refs, admin who acted)
      payment_receipt.py         # PaymentReceipt (Telegram file_id/unique_id, message/chat refs)
      admin_action.py             # AdminAction (audit log: who did what, to what, when)
    repositories/             # Thin data-access layer per model (order/config/product/user/admin_action)
  services/
    user_service.py           # get_or_create_user
    order_service.py           # order lifecycle incl. atomic config assignment on approval
    payment_service.py          # payment info formatting, receipt records, admin notification fan-out
    config_service.py            # config counts, product lookups for the "add config" flow
    product_service.py            # product-related helpers
    statistics_service.py          # aggregate stats for the admin dashboard
  bot/
    handlers/                  # one router per feature area (see below)
    keyboards/                  # inline/reply keyboard builders per feature area
    filters/admin.py             # AdminFilter — checks sender's Telegram ID against ADMIN_IDS
    middlewares/database.py       # injects a DB session into every handler call
    states/__init__.py             # aiogram FSM state groups (UserStates, AdminStates)
alembic/                        # migration environment + versions (001_initial_migration)
tests/                           # pytest suite (23 tests) with async fixtures in conftest.py
seed.py                           # dev-only script to create an admin user, sample products, and configs
Dockerfile, docker-compose.yml     # containerized bot + Postgres
requirements.txt, pyproject.toml    # dependency and tooling config
```

### Handlers, one router per concern

- `user_commands.py` — `/start`, `/help`, back-to-menu, and reply-keyboard text handlers for "راهنما" (help) and "پشتیبانی" (support)
- `purchase.py` — product listing, product selection → order creation → payment info, retry payment
- `receipt.py` — receipt photo upload, admin notification fan-out
- `user_orders.py` — a customer's own order history
- `admin_commands.py` — entry point into the admin panel
- `admin_orders.py` — paginated/filterable order list, order detail view, approve/reject (reject uses FSM to collect a reason)
- `admin_config.py` — add/delete configs, product selection for new configs (also FSM-driven)
- `admin_statistics.py` — shop-wide stats and recent users

## Data model

Five tables, related mostly by Telegram ID rather than foreign keys where the relationship crosses the "Telegram identity" boundary — a deliberate choice noted repeatedly in the code as **"Bug #3 fix"**: `Order.user_id`, `Order.admin_id`, `Config.assigned_to_user_id`, and `AdminAction.admin_id` all store raw Telegram IDs with no FK constraint to `users.id`, and are joined to `User` via `viewonly` relationships on `telegram_id`. This means a user row doesn't strictly need to exist yet for an order to reference them.

- **User** — Telegram identity (`telegram_id`, username, first/last name). `is_admin` is a property that always returns `False`; actual admin status is decided purely by `ADMIN_IDS` in settings, not stored per-user.
- **Product** — name, description, price (`Numeric(10,2)`), currency (defaults to `"تومان"`), duration in days, protocol label, active flag.
- **Config** — a single credential string (`config_text`), tied to a product, with status `AVAILABLE` or `ASSIGNED`, and once assigned, the owning user's Telegram ID and the order that consumed it.
- **Order** — the purchase record: product, amount, unit price, currency, and a status enum (`PENDING_PAYMENT → RECEIPT_SUBMITTED → APPROVED/REJECTED/COMPLETED`, or `CANCELLED`), plus receipt file references, the acting admin, and rejection reason/timestamps.
- **PaymentReceipt** — the uploaded receipt photo's Telegram `file_id`/`file_unique_id`, plus the message and chat it came from.
- **AdminAction** — a generic audit log (`admin_id`, `action`, `target_type`, `target_id`, JSON `action_metadata`) used to record approvals and rejections.

### Config assignment is done under a row lock

The interesting piece of business logic is `OrderService.approve_order_with_config_assignment`. On approval it opens a transaction, locks the order row (`with_for_update()`), locks and grabs one `AVAILABLE` config for that product with `with_for_update(skip_locked=True)`, flips both records' statuses, stamps `assigned_at`/`approved_at`, writes an `AdminAction` log entry, and returns the config text plus the buyer's Telegram ID so the caller can DM it. `skip_locked=True` means two admins approving orders for the same product at the same time won't hand out the same config or deadlock waiting on each other.

## Configuration

Settings are read from environment variables (see `app/config/settings.py`), typically via a `.env` file:

| Variable | Purpose | Default |
|---|---|---|
| `BOT_TOKEN` | Telegram bot token | *(required)* |
| `DATABASE_URL` | Async Postgres DSN | `postgresql+asyncpg://postgres:postgres@localhost:5432/v2ray_bot` |
| `ADMIN_IDS` | Comma-separated Telegram IDs with admin access | *(required — warns if empty)* |
| `BANK_CARD_NUMBER` | Card number shown to buyers | — |
| `BANK_ACCOUNT_NAME` | Account holder name shown to buyers | — |
| `BANK_NAME` | Bank name shown to buyers | — |
| `SHOP_NAME` | Display name of the shop | `V2Ray Shop` |
| `SUPPORT_USERNAME` | Support contact shown in `/help` | `@support` |
| `LOW_STOCK_THRESHOLD` | Threshold used for low-stock warnings | `5` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

`Settings` also mirrors every attribute in lowercase (e.g. both `settings.BOT_TOKEN` and `settings.bot_token` work), which is why you'll see both styles used across the codebase.

## Running it

### With Docker (recommended)

```bash
cp .env.example .env   # fill in BOT_TOKEN, ADMIN_IDS, bank info, etc.
docker compose up --build
```

`docker-compose.yml` brings up Postgres with a healthcheck and only starts the bot container once the database is ready. The bot runs as a non-root user inside the image.

### Locally

```bash
pip install -r requirements.txt
# or: pip install -e ".[dev]"

# start a local Postgres, then:
alembic upgrade head        # apply migrations
python seed.py               # optional: seed an admin user, sample products, and configs
python -m app.main            # start polling
```

`seed.py` reads the first ID in `ADMIN_IDS` and refuses to run if it isn't set. It's idempotent — it skips seeding if products already exist — and it tolerates minor schema drift by mapping a few common alternate field names (e.g. `duration_days` → `duration`) before constructing model instances.

### Tests

```bash
pytest
```

`pytest.ini` and `pyproject.toml` both configure `asyncio_mode = auto`, so async test functions in `tests/test_bot.py` (23 tests, with shared fixtures in `tests/conftest.py`) run without extra decorators.

## Notable design choices

- **Telegram ID as the join key, not a foreign key.** Anywhere a person is referenced from a table that isn't `users` (orders, configs, admin actions), it's stored as a raw Telegram ID with a `viewonly` SQLAlchemy relationship rather than a real foreign key. This avoids having to pre-create a `User` row before an order or config assignment can reference someone, at the cost of losing DB-level referential integrity on those columns.
- **Admin status lives in config, not the database.** There's no `is_admin` column being checked; `AdminFilter` simply checks the sender's Telegram ID against `ADMIN_IDS` from settings on every admin-only handler.
- **One pending order per user.** `OrderService.user_has_pending_order` blocks a second purchase while one is `PENDING_PAYMENT` or `RECEIPT_SUBMITTED`, keeping the manual-review queue simple.
- **FSM for multi-step admin input.** Both "reject an order" (collect a reason) and "add a config" (collect config text, remembering which product it's for) use aiogram's `FSMContext` to gate a plain-text follow-up message to the right handler.
- **DB session per update.** `DatabaseSessionMiddleware` opens a session for every incoming message/callback and injects it into the handler, rather than each handler managing its own session lifecycle.

## Known limitations

- No payment gateway — approval is entirely manual and trust-based on the admin visually checking the receipt photo.
- No refund or cancellation flow beyond `REJECTED`/`CANCELLED` statuses existing in the enum; the reject path is the only one wired up in the handlers shown here.
- `LOW_STOCK_THRESHOLD` is defined in settings but isn't obviously wired into a handler in this snapshot — worth checking before relying on a low-stock alert.
- Config text is stored and sent as plain text with no expiry tracking tied to the product's `duration` field, so nothing in the bot itself revokes access when a subscription period ends.

---

*Generated from a read of the repository source (`app/`, `alembic/`, `tests/`, and root config files) rather than the existing README, which currently only contains a title.*
 