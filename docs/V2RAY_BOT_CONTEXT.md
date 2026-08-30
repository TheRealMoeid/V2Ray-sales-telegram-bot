# V2Ray Sales Telegram Bot — Project Context

> This file is a knowledge base for AI models working with this codebase. It is based on direct inspection of the source code (not just the README), current as of the repository state at the time of writing. It supersedes the bug-focused narrative in `(DONE)V2Ray_Bot_Code_Review.md` and `BUGS.md` — those documents described earlier, broken states of this repo; nearly everything in them has since been fixed (see §7 below for the short list of what's still open).

Repository: https://github.com/TheRealMoeid/V2Ray-sales-telegram-bot

---

## 1. Project Overview

### Name and purpose
A Telegram bot ("V2ray shop bot") that sells pre-generated V2Ray/VLESS/VMess/Trojan proxy configuration strings. It is a small manual storefront, not a full e-commerce platform: an admin stocks config strings against products, customers buy with card-to-card bank transfer, and a human admin manually reviews and approves each payment receipt before the config is released. There is no payment gateway integration. All bot-facing text is in Persian.

### What the bot does
- Lets customers browse active products (each product represents a subscription plan: name, price, duration in days, protocol).
- Creates an order when a customer picks a product, and shows them bank transfer details.
- Accepts a photo of the payment receipt from the customer.
- Notifies all configured admins (text + the receipt photo) when a receipt is submitted.
- Lets an admin approve or reject the order from an inline panel.
- On approval: atomically claims one `AVAILABLE` config row for that product, marks it `ASSIGNED`, marks the order `COMPLETED`, and DMs the config string directly to the buyer.
- On rejection: prompts the admin for a free-text reason (via FSM), stores it, and shows it to the customer.
- Gives customers an order-history view.
- Gives admins an inline panel for config inventory management, order review/pagination/filtering, and shop statistics (users, orders by status, sales totals for today/week/month, config stock levels). **The "recent users" list inside this panel currently crashes — see §7.**

### Main user (customer) workflow
1. `/start` — registers/updates the user row (keyed by Telegram ID) and shows the main reply-keyboard menu. Profile fields (`username`/`first_name`/`last_name`) are refreshed on every call, so they don't go stale if the person changes them on Telegram.
2. "خرید کانفیگ" (Buy config) — lists active products that currently have stock.
3. Selecting a product creates an `Order` in `PENDING_PAYMENT` status and shows the bank card number, account holder name, and bank name.
4. Customer sends a photo of the payment receipt. This is stored as a `PaymentReceipt` row, the order flips to `RECEIPT_SUBMITTED`, and every admin ID in config is notified.
5. Customer waits. An admin approves or rejects.
   - Approved → the bot atomically assigns an available config and DMs it to the customer (to the buyer's Telegram ID, not the approving admin's); order becomes `COMPLETED`.
   - Rejected → the customer is shown the admin's actual typed rejection reason; order becomes `REJECTED`.
6. A customer can only have one order "in flight" (`PENDING_PAYMENT` or `RECEIPT_SUBMITTED`) at a time — a second purchase attempt is blocked with a warning until the current one resolves.
7. "سفارش‌های من" (My orders) shows the customer's own order history and per-order status.

### Main admin workflow
Admin status is **not** a database flag — it's determined purely by checking whether the caller's Telegram ID is in the `ADMIN_IDS` environment variable, enforced via an `AdminFilter` aiogram filter applied to every admin-only handler.

`/admin` (or the `admin_panel` callback) opens an inline panel with:
- **Orders**: paginated list of all orders, optionally filtered by status; tapping an order shows full details, and if it's `RECEIPT_SUBMITTED`, shows Approve/Reject buttons. Pagination is correct across all pages (the list handed to the keyboard builder is already the current page's rows — it is not re-sliced a second time).
- **Approve order**: atomically locks the order row and an available config row (`SELECT ... FOR UPDATE`, with `SKIP LOCKED` on the config), assigns the config, marks the order `COMPLETED`, logs an `AdminAction`, and sends the config to the buyer's Telegram ID (resolved via the order, not the approving admin's own chat).
- **Reject order**: sets an FSM state waiting for a text reason, reads the admin's actual next message, then stores the rejection and logs an `AdminAction`.
- **Configs**: view available/assigned counts, add a new config (validated to start with `vless://`, `vmess://`, or `trojan://`, tied to a specific product stored via FSM state), or delete an unassigned (`AVAILABLE`) config — deletion is routed through `ConfigService`/`ConfigRepository`, which refuses to delete anything that isn't still `AVAILABLE`, so already-sold configs can't be destroyed.
- **Statistics**: total users/orders, orders broken down by status (including a correctly-populated "submitted"/`RECEIPT_SUBMITTED` count), total/today/week/month completed sales, available vs. assigned config counts.
- **Users**: intended to show the 10 most recently registered users — **currently throws a `NameError` on every open; see §7.**

### Overall architecture
Layered, single-process async application:

```
Telegram (long polling)
   → aiogram Dispatcher/Routers (app/bot/handlers)
      → per-request DB session injected by middleware (app/bot/middlewares)
         → Service layer (app/services) — business logic, transactions
            → Repository layer (app/database/repositories) — data access per model
               → SQLAlchemy 2.0 async ORM models (app/database/models)
                  → PostgreSQL
```

Key architectural points:
- **No FastAPI/web server** — the bot runs via `dp.start_polling()`, not webhooks.
- **Telegram ID is the identity key everywhere**, not the internal `users.id` primary key. `Order.user_id`, `Order.admin_id`, `Config.assigned_to_user_id`, and `AdminAction.admin_id` all store raw Telegram IDs with no foreign-key constraint to `users.id` — this is called out repeatedly in code comments as "Bug #3 fix" (a legacy comment name; it is now the settled, intentional design, not an open bug). The `User` model exposes `orders`, `admin_orders`, `configs`, and `admin_actions` as `viewonly=True` SQLAlchemy relationships joined on `telegram_id == foreign(...)` rather than real FKs, specifically to support this design without breaking ORM convenience access.
- **Config assignment race safety**: approving an order and handing out a config is done inside a single `session.begin()` block using `SELECT ... FOR UPDATE` (and `SKIP LOCKED` when picking an available config), so two admins approving concurrently — or an admin approving while stock runs out — can't double-assign the same config.
- **FSM (aiogram's `FSMContext`)** is used for short multi-step admin flows: entering a rejection reason, and submitting a new config's text/choosing which product it belongs to. State data (like `product_id` or `order_id`) is stashed via `state.update_data(...)` and retrieved in the next message handler. The plain-text config-submission handler is gated behind `AdminStates.waiting_for_config`, so it no longer intercepts unrelated admin text messages (e.g. a rejection reason).
- Handlers are split by concern into separate `Router` instances (one per file) and all registered onto a single `Dispatcher` in `app/main.py`.
- Every message/callback goes through `DatabaseSessionMiddleware`, which opens a fresh `AsyncSession` per update and injects it into the handler via aiogram's `data["session"]` dependency-injection mechanism (so handlers just declare a `session: AsyncSession` parameter).
- Both inline-keyboard callback flows and legacy reply-keyboard text button flows exist for the same actions (e.g. "خرید کانفیگ" as both a callback and a plain text match), guarded by a small `_no_active_state(...)` filter helper so these text handlers don't fire while an FSM flow is mid-flight.
- There are two handlers registered for the `admin_panel` callback (one in `admin_commands.py`, one in `admin_orders.py`). Because `admin_commands_router` is included first in `main.py`, the one in `admin_orders.py` is dead code (never fires) — harmless today, but worth cleaning up rather than extending.

---

## 2. Technology Stack

| Technology | Version constraint | Role in this project |
|---|---|---|
| **Python** | ≥ 3.12 (per `pyproject.toml`; Dockerfile uses `python:3.12-slim`) | Runtime. |
| **aiogram** | `>=3.4.0,<4.0.0` | The Telegram bot framework. Used in its aiogram-3 style: `Router` objects per handler module, `Dispatcher.include_router(...)`, `F.data == ...` / `F.data.startswith(...)` / `F.data.regexp(...)` magic filters for callback routing, `Command("start")` filters, `BaseFilter` subclass (`AdminFilter`) for admin gating, `BaseMiddleware` for DB session injection, and `FSMContext`/`StatesGroup` for multi-step conversations. Polling (not webhooks) is used, started via `dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())`. Default parse mode is HTML (`DefaultBotProperties(parse_mode=ParseMode.HTML)`), though individual handlers that build Markdown-formatted text (backtick code blocks, bold) explicitly pass `parse_mode="Markdown"` — this is applied consistently now in `purchase.py`, `admin_orders.py`, and `admin_config.py`.
| **SQLAlchemy** | `>=2.0.0,<3.0.0` | ORM, used exclusively in its async, 2.0-style declarative form: `DeclarativeBase` subclass (`Base`), `Mapped[...]`/`mapped_column(...)` typed columns, `select(...)` statements executed via `AsyncSession.execute(...)`, and explicit `relationship(...)` including `viewonly=True` relationships with custom `primaryjoin` expressions for the Telegram-ID-based joins described above.
| **asyncpg** | `>=0.29.0,<1.0.0` | Async PostgreSQL driver underneath SQLAlchemy's async engine (`postgresql+asyncpg://...` connection string).
| **PostgreSQL** | 15 (per `docker-compose.yml`, `postgres:15-alpine`) | The only supported database backend. |
| **Alembic** | `>=1.13.0,<2.0.0` | Schema migrations; `alembic/versions/` holds the migration history, `alembic/env.py` wires it to the app's SQLAlchemy metadata/`DATABASE_URL`. **The single existing migration (`001_initial_migration`) is drifted from the current models** (wrong column names/types in several tables, missing columns) — see §7. In practice, `init_db()`'s `create_all()` is what actually provisions the schema today, not Alembic. |
| **python-dotenv** | `>=1.0.0,<2.0.0` | Loads `.env` into `os.environ` inside `app/config/settings.py` via `load_dotenv()`. |
| **Docker / docker-compose** | — | `Dockerfile` builds a slim Python 3.12 image, installs `gcc`/`libpq-dev` for building `asyncpg`/psycopg-related wheels, runs as a non-root `botuser`, and starts with `python -m app.main`. `docker-compose.yml` runs the bot alongside a `postgres:15-alpine` service with a healthcheck gate (`pg_isready`) so the bot container only starts after Postgres is ready. |
| **pytest / pytest-asyncio** | `>=8.0.0` / `>=0.23.0` | Test suite (`tests/test_bot.py`, `tests/conftest.py`); `pytest.ini`/`pyproject.toml` set `asyncio_mode = "auto"`. The suite is entirely mock-based (`AsyncMock`/`MagicMock`) — no test spins up a real or in-memory database, so integration-level regressions (like the current `admin_statistics.py` crash) are not caught by `pytest` passing. |
| **ruff / black** | dev-only | Linting/formatting (line length 100, target py312). |
| **aiofiles** | `>=23.0.0` | Listed as a dependency (async file I/O helper); not central to the core purchase/approval flow observed in the handlers. |

### Configuration management
All configuration lives in `app/config/settings.py`, a single `Settings` class instantiated once as a module-level `settings` object. It reads from environment variables (loaded from `.env` via `python-dotenv`) with sensible defaults for non-critical values:
- `BOT_TOKEN`, `DATABASE_URL` (defaults to a local `postgresql+asyncpg://postgres:postgres@localhost:5432/v2ray_bot`), `ADMIN_IDS` (comma-separated string parsed into `List[int]`)
- Bank info: `BANK_CARD_NUMBER`, `BANK_ACCOUNT_NAME`, `BANK_NAME`
- Shop info: `SHOP_NAME`, `SUPPORT_USERNAME`
- `LOW_STOCK_THRESHOLD` (int, default 5) — not currently wired into any handler
- `LOG_LEVEL` (default `INFO`)

The constructor also accepts these as direct keyword args (used by tests to construct isolated `Settings` instances), and for convenience it mirrors every attribute onto a lowercase alias (e.g. both `settings.BOT_TOKEN` and `settings.bot_token` work) — handler code uses both casings interchangeably. `Settings.validate()` raises if `BOT_TOKEN`, `DATABASE_URL`, or `ADMIN_IDS` are missing, though `app/main.py`'s own `main()` does its own manual checks/`sys.exit(1)` rather than calling `validate()` directly (and only logs a warning, not a hard exit, if `ADMIN_IDS` is empty).

---

## 3. Project Structure

```text
.
├── app/
│   ├── main.py                        # Bot/Dispatcher bootstrap: creates Bot+Dispatcher,
│   │                                     registers routers & middleware, startup/shutdown
│   │                                     hooks (init_db, logging bot identity), start_polling()
│   ├── config/
│   │   └── settings.py                # Settings class reading env vars via python-dotenv;
│   │                                     module-level `settings` singleton
│   ├── database/
│   │   ├── session.py                 # Base (DeclarativeBase), async engine, async_session_maker
│   │   │                                 (aliased as async_session), init_db()/close_db(), get_db()
│   │   ├── models/
│   │   │   ├── user.py                # User: Telegram identity + viewonly relationships keyed
│   │   │   │                            on telegram_id (orders, admin_orders, configs, admin_actions)
│   │   │   ├── product.py             # Product: name, price, currency, duration (days), protocol,
│   │   │   │                            is_active flag; has configs/orders relationships
│   │   │   ├── config.py              # Config: one VLESS/VMess/Trojan string; ConfigStatus enum
│   │   │   │                            (AVAILABLE/ASSIGNED); FK to product, nullable FK to order
│   │   │   ├── order.py               # Order: OrderStatus enum (PENDING_PAYMENT,
│   │   │   │                            RECEIPT_SUBMITTED, APPROVED, REJECTED, COMPLETED,
│   │   │   │                            CANCELLED); amount/currency/unit_price, receipt file refs,
│   │   │   │                            rejection_reason, timestamps for created/updated/approved/
│   │   │   │                            rejected; relationships to product/config/receipt
│   │   │   ├── payment_receipt.py     # PaymentReceipt: telegram file_id/file_unique_id,
│   │   │   │                            message_id/chat_id, 1:1 with Order
│   │   │   └── admin_action.py        # AdminAction: audit log (admin_id, action, target_type,
│   │   │                                target_id, JSON action_metadata, created_at)
│   │   └── repositories/              # Thin data-access layer, one repo class per model, each
│   │       ├── user_repository.py     #   wrapping session.execute(select(...)) calls plus
│   │       ├── product_repository.py  #   create/update/delete/count helpers. Repositories contain
│   │       ├── config_repository.py   #   no business rules beyond query construction and the
│   │       ├── order_repository.py    #   FOR UPDATE / SKIP LOCKED locking used for atomic
│   │       └── admin_action_repository.py  # config assignment and order approval.
│   ├── services/                      # Business logic layer, called from handlers; each wraps
│   │   ├── user_service.py            #   one or more repositories
│   │   ├── product_service.py         #   (currently unused — no handler calls into it)
│   │   ├── config_service.py          # available-config queries/counts, atomic assignment entry
│   │   │                                point (assign_config_to_order), config creation/deletion
│   │   ├── order_service.py           # order CRUD, user_has_pending_order guard,
│   │   │                                approve_order_with_config_assignment (the core atomic
│   │   │                                approve+assign+notify transaction), reject_order,
│   │   │                                order counts / sales sum
│   │   ├── payment_service.py         # payment-info text formatting (unused — purchase.py builds
│   │   │                                its own text inline), PaymentReceipt creation,
│   │   │                                notify_admins_new_receipt (fans a text+photo notification
│   │   │                                out to every ADMIN_IDS entry, tolerant of a missing User row)
│   │   └── statistics_service.py      # aggregate counts/sums for the admin stats screen
│   └── bot/
│       ├── handlers/                  # aiogram Router modules, one per feature area
│       │   ├── user_commands.py       # /start, /help, back-to-menu, reply-keyboard text
│       │   │                            equivalents for help/support buttons
│       │   ├── purchase.py            # buy_config → product list → select_product → create
│       │   │                            order → show payment info; retry_payment; reply-keyboard
│       │   │                            "خرید کانفیگ" text equivalent
│       │   ├── receipt.py             # F.photo handler that turns a photo into a PaymentReceipt
│       │   │                            + flips order to RECEIPT_SUBMITTED + notifies admins;
│       │   │                            send_receipt callback (prompts for the photo)
│       │   ├── user_orders.py         # my_orders / view_order callbacks + reply-keyboard
│       │   │                            "سفارش‌های من" text equivalent
│       │   ├── admin_commands.py      # /admin and admin_panel callback → opens admin menu
│       │   ├── admin_orders.py        # paginated/filterable order list, order detail view,
│       │   │                            approve_order / reject_order (+ FSM reason capture);
│       │   │                            also registers a dead/shadowed admin_panel handler
│       │   ├── admin_config.py        # config inventory: list counts, add config (FSM: pick
│       │   │                            product → submit config text), delete config (routed
│       │   │                            through the service layer's AVAILABLE-only guard)
│       │   └── admin_statistics.py    # admin_statistics and admin_users callbacks — the latter
│       │                                currently crashes with a NameError, see §7
│       ├── keyboards/                 # Static/dynamic InlineKeyboardMarkup / ReplyKeyboardMarkup
│       │   ├── main_menu.py           #   builders, one module per screen (admin_menu,
│       │   ├── admin_menu.py          #   admin_orders — includes pagination/filter buttons,
│       │   ├── admin_orders.py        #   admin_config, payment_info, product_list, user_orders)
│       │   ├── admin_config.py
│       │   ├── payment_info.py
│       │   ├── product_list.py        #   (get_product_confirmation() here is unused dead code)
│       │   └── user_orders.py
│       ├── middlewares/
│       │   └── database.py            # DatabaseSessionMiddleware: opens one AsyncSession per
│       │                                 update and injects it as data["session"] for all
│       │                                 message and callback_query handlers
│       ├── filters/
│       │   └── admin.py               # AdminFilter(BaseFilter): True iff event.from_user.id is
│       │                                 in settings.admin_ids — the sole admin gate
│       └── states/
│           └── __init__.py            # UserStates and AdminStates (StatesGroup) — FSM states for
│                                         product selection/receipt waiting (user) and product/
│                                         config creation, config text entry, rejection reason
│                                         entry (admin)
├── alembic/                           # Migration environment (env.py) + alembic/versions/
│                                         (drifted from current models — see §7)
├── alembic.ini
├── seed.py                            # Dev-data seed script: creates an admin user, sample
│                                         products, and sample AVAILABLE configs; requires
│                                         ADMIN_IDS to be set, exits otherwise (no hardcoded
│                                         fallback admin ID)
├── tests/
│   ├── conftest.py                    # Test fixtures (mock session/user/product/config/order)
│   └── test_bot.py                    # Mock-based tests covering models, services, filters,
│                                         and settings parsing — no DB/integration coverage
├── requirements.txt                   # Pinned dependency ranges (mirrors pyproject.toml)
├── pyproject.toml                     # Project metadata, dependency list, black/ruff/pytest config
├── pytest.ini
├── Dockerfile                         # python:3.12-slim, non-root botuser, CMD ["python","-m","app.main"]
├── docker-compose.yml                 # bot + postgres:15-alpine services, healthcheck-gated startup
├── KNOWN_ISSUES.md                    # currently open bugs, schema drift, and dead code
└── README.md
```

---

## 4. Data Model Details

### `User`
- `id` (internal PK, `BigInteger`), `telegram_id` (unique, indexed — the real identity key used everywhere else), `username`, `first_name`, `last_name`, timestamps.
- `is_admin` is a **property that always returns `False`** — admin status is deliberately never derived from the DB; it's explicitly noted in code that it comes from `ADMIN_IDS` via `AdminFilter` instead.
- `orders`, `admin_orders`, `configs`, `admin_actions` are all `viewonly=True` relationships joined via `primaryjoin="User.telegram_id == foreign(Other.some_id)"` rather than real foreign keys, because `Order.user_id`, `Order.admin_id`, `Config.assigned_to_user_id`, and `AdminAction.admin_id` intentionally store raw Telegram IDs with no FK constraint back to `users.id`.

### `Product`
- `name`, `description`, `price` (`Numeric(10,2)`, mapped in Python as `float` — a type-hint mismatch, since SQLAlchemy returns `Decimal` here by default; not currently causing failures), `currency` (default `"تومان"`), `duration` (int, days, default 30), `protocol` (default `"VLESS"`), `is_active` (bool). `deactivate_product` is a soft delete (`is_active = False`), not a row delete.
- Has `configs` and `orders` relationships.
- `ProductService`/`ProductRepository` support full CRUD on this model but are currently **unused** — there's no admin handler for creating or editing products through the bot; that only happens via `seed.py` or direct DB access.

### `Config`
- One row = one literal `vless://`/`vmess://`/`trojan://` string (`config_text`, `Text`).
- `status`: `ConfigStatus` enum — `AVAILABLE` or `ASSIGNED`.
- `assigned_to_user_id` (Telegram ID, no FK), `order_id` (nullable, unique FK to `orders.id`, `ON DELETE SET NULL`), `assigned_at`.
- Deletion (`ConfigRepository.delete`, and the handler that calls into it via `ConfigService`) only succeeds if the config is still `AVAILABLE` — an admin cannot destroy a config that's already been sold.

### `Order`
- `user_id` (Telegram ID, no FK), `product_id` (FK, `ON DELETE RESTRICT` — a product can't be deleted while orders reference it).
- `amount`, `unit_price` (`Numeric(10,2)`, mapped as `float`), `currency`.
- `status`: `OrderStatus` enum — `PENDING_PAYMENT → RECEIPT_SUBMITTED → (APPROVED | COMPLETED | REJECTED)`, plus `CANCELLED`. In practice the approval path in `OrderService` jumps straight from `RECEIPT_SUBMITTED` to `COMPLETED` (it doesn't pass through a separate `APPROVED` row state — `APPROVED` exists in the enum and is used by a lower-level, currently-unused `OrderRepository.approve_order` helper, but the actual admin-approve handler calls the higher-level `OrderService.approve_order_with_config_assignment`, which sets `COMPLETED` directly).
- `receipt_file_id` / `receipt_file_unique_id`: Telegram file identifiers for the receipt photo. Both are correctly populated by `receipt.py` (duplicated here and in `PaymentReceipt`, which is intentional redundancy, not a bug).
- `admin_id` (Telegram ID, no FK) — which admin acted on it; `rejection_reason` (now populated from the admin's actual FSM-captured text, not a placeholder); `created_at`/`updated_at`/`approved_at`/`rejected_at`.

### `PaymentReceipt`
- 1:1 with `Order` (`order_id` unique FK, `ON DELETE CASCADE`).
- Stores `telegram_file_id`, `telegram_file_unique_id`, plus the original `message_id`/`chat_id` the photo was sent in. `chat_id` is required (`nullable=False`) and is correctly set from `message.chat.id` in the handler.

### `AdminAction`
- Generic audit log: `admin_id` (Telegram ID, no FK), `action` (string, e.g. order approval/rejection), `target_type` (`"order"`, `"config"`, etc.), `target_id`, `action_metadata` (JSON blob for arbitrary extra detail — correctly populated via the `action_metadata=` kwarg, not silently dropped), `created_at`. Written by `AdminActionRepository` whenever `OrderService.approve_order_with_config_assignment` or `reject_order` runs.

---

## 5. Core Business Logic Worth Knowing

- **`OrderService.approve_order_with_config_assignment`** (used by the real approve-order handler) is the single most important transaction in the codebase: inside one `async with session.begin()` block it (1) locks the target order row with `SELECT ... FOR UPDATE` and checks it's still `RECEIPT_SUBMITTED`, (2) locks one `AVAILABLE` config row for that product with `SELECT ... FOR UPDATE SKIP LOCKED` (so concurrent approvals never contend on rows another transaction is already claiming), (3) flips the config to `ASSIGNED` and the order to `COMPLETED`, (4) writes an `AdminAction` log entry, and (5) returns `(config_text, buyer_telegram_id)` so the caller can DM the buyer — not the approving admin — outside the transaction. Raises `ValueError` (with Persian messages) if the order doesn't exist, isn't in `RECEIPT_SUBMITTED` status, or no config is available.
- **`OrderService.user_has_pending_order`** is the guard that blocks a customer from opening a second order while one is still `PENDING_PAYMENT` or `RECEIPT_SUBMITTED`.
- **Config text validation** happens in the handler layer (`admin_config.py`), not the service/model layer: submitted text must start with `vless://`, `vmess://`, or `trojan://` or it's rejected with a Persian error and the FSM state is left in place for retry. The handler is gated behind `AdminStates.waiting_for_config`, so it no longer intercepts arbitrary admin text (e.g. a rejection reason typed for a different flow).
- **Admin notification fan-out** (`PaymentService.notify_admins_new_receipt`) iterates `settings.ADMIN_IDS` and sends a text summary + the receipt photo to each; failures for one admin are caught and logged so one bad chat doesn't block notifying the rest. It also tolerates the edge case where no `User` row exists yet for the buyer (falls back to a "نامشخص" display name instead of crashing).
- **Reply-keyboard vs inline-keyboard duplication**: several actions (buy, view orders, help, support) are wired twice — once as inline-keyboard callback handlers, once as plain-text matches against a persistent reply keyboard (`F.text.contains(...)`) — each guarded by a small local `_no_active_state*` filter function that checks `await state.get_state() is None`, so these text shortcuts don't accidentally fire mid-FSM-flow (e.g., while an admin is in the middle of typing a rejection reason).
- **Order-list pagination** (`admin_orders.py` + `AdminOrdersKeyboard`) fetches only the current page's rows from the DB via `OFFSET`/`LIMIT` and passes that already-paginated list straight to the keyboard builder, which renders it without re-slicing. All pages are reachable, not just page 1.

---

## 6. Notable Design Choices / Gotchas for an AI Working on This Code

- Do **not** add foreign keys from `Order.user_id`, `Order.admin_id`, `Config.assigned_to_user_id`, or `AdminAction.admin_id` to `users.id` — this is an intentional, settled design (comments call it "Bug #3 fix", a legacy name from an earlier audit — it is not an open issue) to decouple these fields from internal user row lifecycle and key them directly on Telegram ID instead. Use the existing `viewonly` relationships on `User` for reads.
- `User.is_admin` is always `False` by design — admin checks must go through `AdminFilter` / `settings.ADMIN_IDS`, not this property.
- Config/order approval logic must stay inside a locking transaction (`with_for_update`, `skip_locked` for config selection) to avoid double-selling a config — don't refactor `approve_order_with_config_assignment` into separate non-atomic steps.
- `Settings` mirrors every attribute in both upper and lower case; code in this repo uses both `settings.BOT_TOKEN` and `settings.bot_token` interchangeably, so either works.
- `ConfigRepository.delete` (and the handler path that calls it) intentionally refuses to delete a config unless it's still `AVAILABLE` (protects already-sold/assigned configs from deletion). Don't bypass this by calling `session.delete()` directly on a `Config` object from a handler.
- There are two parallel entry points for several user actions (inline callback vs. reply-keyboard text); if adding a new customer-facing action, consider whether it needs both to match existing UX conventions.
- All user-facing strings are Persian; keep new strings consistent in language and tone (informal storefront Persian with emoji section markers) if extending the bot.
- The **Alembic migration is not currently trustworthy** — don't assume `alembic upgrade head` produces a schema matching the models. `init_db()`'s `create_all()` is what actually provisions the schema in this repo's `main()`/Docker startup path today. Regenerate the migration before relying on Alembic for a real deployment.
- Several service classes/methods look load-bearing but are dead code (`ProductService`, `OrderRepository.approve_order`, `PaymentService.get_payment_info`/`validate_receipt_photo`, `ProductListKeyboard.get_product_confirmation`). Check whether a handler actually calls something before assuming it's part of the live flow.

---

## 7. Current Known Gaps (read before starting new work)

This section is the up-to-date replacement for the older bug-report documents. Full detail lives in `KNOWN_ISSUES.md`; summary here:

- 🔴 **`admin_statistics.py::handle_admin_users` crashes with `NameError`** every time it runs (references `name`/`user` before they're assigned, outside the loop that defines them). The "👥 کاربران" admin screen is currently non-functional. This is a new regression not previously documented.
- 🟡 **Alembic migration (`001_initial_migration.py`) is out of sync with the current models** (wrong types/names on `products`, `orders`, `configs`, `payment_receipts`, plus a stray `users.is_admin` column with no model equivalent). Masked today by `create_all()`, but would break a real `alembic upgrade head` run against a fresh DB.
- 🟡 **Dead code**: `OrderRepository.approve_order`, `ProductService`/`ProductRepository`, `PaymentService.get_payment_info`/`validate_receipt_photo`, `ProductListKeyboard.get_product_confirmation`, and a shadowed duplicate `admin_panel` callback handler in `admin_orders.py`.
- 🟢 **Minor**: `Numeric` columns typed as `float` instead of `Decimal`; test suite is mock-only with no DB/integration coverage.

Everything else previously reported in `(DONE)V2Ray_Bot_Code_Review.md` and `BUGS.md` (the startup-blocking syntax errors, the `Order.user_id` FK mismatch, config sent to the wrong chat, missing imports, missing `chat_id`, broken pagination, unsafe config deletion, stale user profiles, etc.) has been verified fixed in the current code and should be treated as resolved history, not open work.
