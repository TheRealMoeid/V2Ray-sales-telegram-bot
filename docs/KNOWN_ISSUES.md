# Known Issues — V2Ray Sales Telegram Bot

This file replaces the numbered bug lists in `(DONE)V2Ray_Bot_Code_Review.md` and
`BUGS.md`. Those two documents were point-in-time audits of earlier, broken states
of the repository — almost everything they flagged has since been fixed. This file
keeps only the items from those reports that are **still true against the current
code**.

Those two files should be moved to a `docs/history/` folder (or deleted) once this
file is in place, so nobody mistakes a resolved historical bug for a live one.

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
  current file contains ~24 test methods (30, including
  `tests/test_admin_users_handler.py` — see the "Recently Fixed" section below).
  Minor, but worth re-counting whenever the suite changes.
- **Mock-only unit test suite**: `tests/test_bot.py` and
  `tests/test_admin_users_handler.py` use `AsyncMock`/`MagicMock` throughout and
  never exercise a real database or the full handler call chain. This is fine for
  catching logic bugs like the `handle_admin_users` regression below, but on its
  own it would **not** catch schema-level problems — which is exactly what
  happened with the Alembic drift (see "Recently Fixed"). That gap is now
  partially closed: `tests/test_alembic_schema_sync.py` is a real integration
  suite against Postgres that specifically guards against migration/model drift
  reappearing. The purchase → receipt → approve handler flow itself is still only
  covered by mocks; an end-to-end integration test for that flow would still be
  worth adding.

---

## ✅ Recently Fixed

### Alembic migration schema drift — FIXED

**Files:** `alembic/versions/001_initial_migration.py` (deleted) →
`alembic/versions/001_baseline_schema.py` (new), `alembic/env.py`,
`app/database/session.py`, `Dockerfile`, `entrypoint.sh` (new), `README.md`

**Status:** Fixed and verified. Merged to GitHub by Moeid.

**Root cause:** `001_initial_migration.py` was hand-written once and never kept in
sync with the SQLAlchemy models as they evolved. Confirmed drift included:
`products.duration_days` vs. model's `duration`; `Integer` vs. `Numeric(10,2)` for
`products.price`/`orders.amount`/`orders.unit_price`; missing
`orders.unit_price`/`receipt_file_unique_id` and `payment_receipts.chat_id`
columns; `String` vs. native `Enum` for `orders.status`/`configs.status`; a stray
`users.is_admin` column with no model equivalent; `Integer` vs. `BigInteger`
primary keys on every table except `users`; a missing `UNIQUE` constraint on
`configs.order_id`; and — worst of all — a hand-added foreign key from
`admin_actions.admin_id` to `users.id` that contradicts the intentional "Bug #3
fix" design (that column stores a raw Telegram ID, not a `users.id` value, so the
FK would have rejected every audit-log insert if it were ever actually enforced).

**A second, independent bug was found and fixed in the process:**
`alembic/env.py`'s `run_migrations_online()` passed an `async def` function to
`connection.run_sync()`, which requires a plain **synchronous** callable.
`run_sync()` was therefore just constructing a coroutine object without awaiting
it, so `context.configure()`/`context.run_migrations()` never actually executed —
`alembic upgrade head` silently exited `0` while doing nothing at all, for every
migration, regardless of its content. This was masked because
`init_db()`'s `Base.metadata.create_all()` was what actually provisioned the
schema in every real startup path.

**Fix applied (Approach A+ — clean slate & cutover):**
1. Deleted `001_initial_migration.py`; regenerated a baseline
   (`001_baseline_schema.py`) via a real `alembic revision --autogenerate` run
   against an empty Postgres instance, reviewed to confirm no stray FKs on the
   Telegram-ID columns, `Numeric(10,2)` for money columns, native `Enum` types,
   and `BigInteger` PKs throughout.
2. Fixed the `env.py` async/sync bug (async callback → plain `def`, per the
   standard Alembic async recipe) so `alembic upgrade head` actually runs.
3. Removed `Base.metadata.create_all()` from `session.py`'s `init_db()`,
   replacing it with a lightweight `SELECT 1` connectivity check — schema
   management is now exclusively Alembic's job, so a future model change without
   a matching migration fails loudly instead of being silently patched.
4. Added `entrypoint.sh` (runs `alembic upgrade head`, then `exec python -m
   app.main`) and pointed the Docker image's `ENTRYPOINT` at it, so the container
   won't start the bot if migrations fail.
5. Updated `README.md` with the new Alembic-first workflow and an "Upgrading an
   existing deployment" section: any database that already has the correct
   schema via the old `create_all()` behavior needs a one-time `alembic stamp
   head` (not `upgrade head`) since it has no `alembic_version` row yet.

**Verification:**
- `alembic_migration_drift_fix.patch` — applied cleanly (`git apply --check`) to
  a fresh clone.
- `tests/test_alembic_schema_sync.py` — 7 new integration tests against a real
  Postgres instance: `alembic upgrade head` actually creates all 7 tables and
  writes an `alembic_version` row (regression guard for the `env.py` bug); the
  migration produces **zero drift** against `Base.metadata` via
  `alembic.autogenerate.compare_metadata` (the core drift check); no foreign key
  exists on `admin_actions.admin_id`; the specific previously-drifted
  columns/types now match the models; `init_db()` no longer creates tables; and
  the full "existing deployment" `alembic stamp head` → `alembic upgrade head`
  flow is a no-op as documented. **All 7 fail against the pre-fix code** (including
  a caught `NoSuchTableError` and an assertion proving `alembic upgrade head` used
  to do nothing) **and all 7 pass against the fix.**
- Full suite (`tests/test_bot.py` + `tests/test_admin_users_handler.py` +
  `tests/test_alembic_schema_sync.py`, 37 tests total) passes with no
  regressions elsewhere.
- Re-verified independently against a fresh clone of `main` after Moeid merged:
  `alembic upgrade head` against an empty database creates all 7 tables and
  `alembic current` reports the head revision; full 37-test suite passes.

---

### Admin "Users" screen crash (`NameError` regression) — FIXED

**File:** `app/bot/handlers/admin_statistics.py`, `handle_admin_users`

**Status:** Fixed and verified. Merged to GitHub by Moeid.

**Root cause:** The handler referenced the loop variables `name` and `user` on a
line placed *before* the `for` loop that defines them:

```python
# Before (buggy):
users_text = ""
users_text += f"• {_escape_markdown(name)} (ID: `{user.telegram_id}`)\n"   # <- name/user undefined here
users_text += "**۱۰ کاربر اخیر:**\n"

if recent_users:
    for user in recent_users:
        name = f"@{user.username}" if user.username else (user.first_name or "بدون نام")
        users_text += f"• {_escape_markdown(name)} (ID: `{user.telegram_id}`)\n"
```

This raised `NameError: name 'name' is not defined` (or `UnboundLocalError` on
some Python versions) on **every** invocation of the handler, regardless of
whether any users existed. Because the handler's broad `except Exception` block
swallowed the crash, the admin only ever saw a generic "❌ خطایی رخ داد" alert —
the "👥 کاربران" (Users) screen in the admin panel was completely non-functional.

**Fix applied (Approach B — minimal removal + surface `total_users`):**

```python
# After (fixed):
users_text = f"👥 مجموع کاربران: {total_users}\n\n"
users_text += "**۱۰ کاربر اخیر:**\n"

if recent_users:
    for user in recent_users:
        name = f"@{user.username}" if user.username else (user.first_name or "بدون نام")
        users_text += f"• {_escape_markdown(name)} (ID: `{user.telegram_id}`)\n"
else:
    users_text += "_هنوز کاربری ثبت‌نام نکرده._"
```

The two stray lines were removed, the header line was moved before the
`if recent_users:` block, and `total_users` — which was already being queried
via a separate `SELECT count(*)` but never used anywhere — is now displayed at
the top of the screen instead of being dead-computed.

**Verification:**
- `fix_admin_users_nameerror.patch` — 2-line unified diff, applied cleanly to a
  fresh clone.
- `tests/test_admin_users_handler.py` — 7 new tests covering: the core
  regression (handler completes and calls `edit_text` instead of hitting the
  `except` block), the "no users yet" placeholder branch, username/first-name
  fallback logic, Markdown-escaping of special characters in names, and that
  `total_users` is now rendered. All 7 fail against the pre-fix code
  (reproducing the exact `NameError`/`UnboundLocalError`) and all 7 pass
  against the fix.
- Full suite (`tests/test_bot.py` + `tests/test_admin_users_handler.py`, 30
  tests total) passes with no regressions elsewhere.
- Manually verified against a live running bot (Docker) by Moeid: the "👥 ۱۰
  کاربر اخیر" screen now renders the total user count plus the recent-users
  list instead of throwing the generic error alert.

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
- **The admin "Users" screen `NameError` regression** (see "Recently Fixed"
  above) — fixed and verified.
- **The Alembic migration schema drift, including the `env.py` async/sync bug**
  (see "Recently Fixed" above) — fixed and verified.

If any of the above resurfaces, treat it as a regression, not a known issue.
