"""Regression tests for the admin "Users" screen (`handle_admin_users`).

Context
-------
`app/bot/handlers/admin_statistics.py::handle_admin_users` previously crashed
with a `NameError` on every invocation because it referenced the loop
variables `name` and `user` on a line placed *before* the `for` loop that
defines them. The handler swallows the exception via a broad
`except Exception`, so the crash surfaced to the admin only as a generic
"❌ خطایی رخ داد" alert, with `callback.answer(..., show_alert=True)` called
instead of `callback.message.edit_text(...)`.

These tests exercise the handler directly (mocking the DB session and the
aiogram `CallbackQuery`) and assert that:
  1. The handler completes successfully and renders the users screen via
     `edit_text` (this is the core regression check — it would fail with a
     `NameError` bubbling out of the `try` block on the pre-fix code, since
     `callback.message.edit_text` would never be called).
  2. The rendered text is well-formed for both the "has recent users" and
     "no users yet" branches.
  3. The `total_users` count (queried but previously never used in the
     output) is now surfaced in the rendered text.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.admin_statistics import handle_admin_users


def _make_user(telegram_id: int, username: str | None, first_name: str | None) -> MagicMock:
    user = MagicMock()
    user.telegram_id = telegram_id
    user.username = username
    user.first_name = first_name
    user.created_at = datetime.now(timezone.utc)
    return user


def _make_session_with(total_users: int, recent_users: list) -> AsyncMock:
    """Build a mock AsyncSession whose `execute` returns, in order:
    1. the result of the `SELECT count(*) ...` query (`.scalar()`), then
    2. the result of the `SELECT ... ORDER BY created_at DESC LIMIT 10`
       query (`.scalars().all()`).
    This mirrors the two `session.execute(...)` calls made by
    `handle_admin_users`, in call order.
    """
    session = AsyncMock()

    count_result = MagicMock()
    count_result.scalar.return_value = total_users

    recent_result = MagicMock()
    recent_result.scalars.return_value.all.return_value = recent_users

    session.execute = AsyncMock(side_effect=[count_result, recent_result])
    return session


def _make_callback() -> AsyncMock:
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


class TestHandleAdminUsersRegression:
    """Direct regression coverage for the NameError fix."""

    @pytest.mark.asyncio
    async def test_does_not_raise_and_renders_screen_with_users(self):
        """Core regression test.

        On the buggy code, `users_text += f"...{name}...{user}..."` runs
        before `name`/`user` are ever bound, raising `NameError` inside the
        handler's own `try` block. The `except Exception` then calls
        `callback.answer(..., show_alert=True)` and `edit_text` is NEVER
        called. This test fails against the pre-fix code and passes once
        the stray line is removed.
        """
        users = [
            _make_user(111, username="alice", first_name=None),
            _make_user(222, username=None, first_name="Bob"),
        ]
        session = _make_session_with(total_users=42, recent_users=users)
        callback = _make_callback()

        await handle_admin_users(callback, session)

        # The handler must have reached the success path, not the except block.
        callback.message.edit_text.assert_awaited_once()
        callback.answer.assert_awaited_once_with()  # plain ack, no show_alert
        assert callback.answer.await_args.kwargs.get("show_alert") is None

        rendered_text = callback.message.edit_text.await_args.kwargs["text"]

        # Both users should appear, correctly formatted.
        assert "alice" in rendered_text
        assert "111" in rendered_text
        assert "Bob" in rendered_text
        assert "222" in rendered_text

    @pytest.mark.asyncio
    async def test_does_not_swallow_exception_as_generic_error(self):
        """Explicit negative check: the handler must not fall into its
        `except Exception` branch (which is what the NameError regression
        looked like to the admin — a generic error alert with no real
        content)."""
        session = _make_session_with(total_users=0, recent_users=[])
        callback = _make_callback()

        await handle_admin_users(callback, session)

        for call in callback.answer.await_args_list:
            assert call.kwargs.get("show_alert") is not True
        assert "خطایی رخ داد" not in "".join(
            str(c) for c in callback.answer.await_args_list
        )


class TestHandleAdminUsersContent:
    """Content/formatting checks for both branches of the handler."""

    @pytest.mark.asyncio
    async def test_no_recent_users_shows_placeholder(self):
        session = _make_session_with(total_users=0, recent_users=[])
        callback = _make_callback()

        await handle_admin_users(callback, session)

        rendered_text = callback.message.edit_text.await_args.kwargs["text"]
        assert "هنوز کاربری ثبت‌نام نکرده" in rendered_text

    @pytest.mark.asyncio
    async def test_username_missing_falls_back_to_first_name(self):
        users = [_make_user(333, username=None, first_name="Reza")]
        session = _make_session_with(total_users=1, recent_users=users)
        callback = _make_callback()

        await handle_admin_users(callback, session)

        rendered_text = callback.message.edit_text.await_args.kwargs["text"]
        assert "Reza" in rendered_text
        assert "333" in rendered_text

    @pytest.mark.asyncio
    async def test_username_and_first_name_missing_falls_back_to_placeholder(self):
        users = [_make_user(444, username=None, first_name=None)]
        session = _make_session_with(total_users=1, recent_users=users)
        callback = _make_callback()

        await handle_admin_users(callback, session)

        rendered_text = callback.message.edit_text.await_args.kwargs["text"]
        assert "بدون نام" in rendered_text

    @pytest.mark.asyncio
    async def test_total_users_count_is_surfaced(self):
        """`total_users` is fetched from the DB but, before this fix, was
        never used anywhere in `users_text`. Approach B surfaces it in the
        rendered output."""
        session = _make_session_with(total_users=57, recent_users=[])
        callback = _make_callback()

        await handle_admin_users(callback, session)

        rendered_text = callback.message.edit_text.await_args.kwargs["text"]
        assert "57" in rendered_text

    @pytest.mark.asyncio
    async def test_markdown_special_characters_in_username_are_escaped(self):
        """Usernames/first names containing Markdown-special characters
        must be escaped via `_escape_markdown`, matching the existing
        convention used elsewhere in this file (e.g. admin_orders.py)."""
        users = [_make_user(555, username=None, first_name="A_B*C`D[E")]
        session = _make_session_with(total_users=1, recent_users=users)
        callback = _make_callback()

        await handle_admin_users(callback, session)

        rendered_text = callback.message.edit_text.await_args.kwargs["text"]
        assert "A\\_B\\*C\\`D\\[E" in rendered_text
