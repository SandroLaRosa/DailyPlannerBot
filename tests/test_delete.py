"""Unit tests for src.modules.delete_logics"""

from __future__ import annotations

import asyncio
import importlib
import sys
import unittest.mock as _umock
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from telegram.ext import ConversationHandler

# ── module-level stubs must be in sys.modules before the import below ─────────
# pylint: disable=wrong-import-position

_TZ = ZoneInfo("Europe/Rome")

# Build a conversation_logics stub that exposes parse_future_dt as a public
# name so tests never have to touch a protected attribute directly.
_conv_stub = _umock.MagicMock()
_conv_stub.parse_future_dt = _umock.MagicMock()  # public alias used by helpers
_conv_stub.cancel = _umock.AsyncMock(return_value=-1)

sys.modules.setdefault("telegram", _umock.MagicMock())
sys.modules.setdefault("telegram.ext", _umock.MagicMock())
sys.modules.setdefault("src.classes.event_manager", _umock.MagicMock())
sys.modules.setdefault("src.classes.event", _umock.MagicMock())
sys.modules.setdefault("src.modules.conversation_logics", _conv_stub)
sys.modules.setdefault("src.modules.timezone_logics", _umock.MagicMock())
sys.modules.setdefault("src.modules.notify", _umock.MagicMock())

import src.modules.delete_logics as _dl_module  # noqa: E402

# fixtures


@pytest.fixture(autouse=True)
def _reload(mocker):
    conv_stub = mocker.MagicMock()
    conv_stub.parse_future_dt = mocker.MagicMock()  # public alias
    conv_stub.cancel = mocker.AsyncMock(return_value=-1)

    stubs = {
        "telegram": mocker.MagicMock(),
        "telegram.ext": mocker.MagicMock(),
        "src.classes.event_manager": mocker.MagicMock(),
        "src.classes.event": mocker.MagicMock(),
        "src.modules.conversation_logics": conv_stub,
        "src.modules.timezone_logics": mocker.MagicMock(TZ=_TZ),
        "src.modules.notify": mocker.MagicMock(),
    }
    stubs["telegram.ext"].ConversationHandler.END = -1
    mocker.patch.dict(sys.modules, stubs)
    importlib.reload(_dl_module)
    yield stubs


# helpers


def _run(coro):
    return asyncio.run(coro)


def _dt(year=2099, month=4, day=28, hour=10) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=_TZ)


def _make_update(mocker, text: str = "placeholder"):
    update = mocker.MagicMock()
    update.effective_chat = mocker.MagicMock()
    update.effective_user = mocker.MagicMock()
    update.message = mocker.MagicMock()
    update.message.text = text
    update.message.reply_text = mocker.AsyncMock()
    return update


def _make_context(mocker, user_data=None, events=None):
    ctx = mocker.MagicMock()
    ctx.user_data = user_data if user_data is not None else {}
    em = mocker.MagicMock()
    em.events = events or {}
    em.remove_event = mocker.MagicMock()
    ctx.bot_data = {"event_manager": em}
    return ctx, em


def _make_event(mocker, name: str, start: datetime, description: str | None = None):
    ev = mocker.MagicMock()
    ev.id = f"id-{name}-{start.hour}"
    ev.name = name
    ev.start_date = start
    ev.description = description
    ev.get_message = mocker.MagicMock(
        return_value=f"{name} alle {start.strftime('%H:%M')}"
    )
    return ev


def _set_parse(return_value):
    """Patch parse_future_dt on the reloaded module for the current test."""
    _dl_module.parse_future_dt = lambda _text: return_value


# start_delete


class TestStartDelete:

    def test_clears_user_data_and_returns_DELETE_NAME(self, mocker):
        ctx, _ = _make_context(mocker, user_data={"stale": True})
        state = _run(_dl_module.start_delete(_make_update(mocker), ctx))
        assert ctx.user_data == {}
        assert state == _dl_module.DELETE_NAME

    def test_sends_exactly_one_message(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker)
        _run(_dl_module.start_delete(update, ctx))
        update.message.reply_text.assert_awaited_once()


# get_delete_name


class TestGetDeleteName:

    def test_no_match_stays_in_DELETE_NAME(self, mocker, _reload):
        ctx, _ = _make_context(mocker, events={})
        state = _run(_dl_module.get_delete_name(_make_update(mocker, "Fantasma"), ctx))
        assert state == _dl_module.DELETE_NAME

    def test_no_match_reply_contains_the_given_name(self, mocker, _reload):
        update = _make_update(mocker, "Fantasma")
        ctx, _ = _make_context(mocker, events={})
        _run(_dl_module.get_delete_name(update, ctx))
        replied = update.message.reply_text.call_args[0][0]
        assert "Fantasma" in replied

    def test_match_stores_name_and_returns_DELETE_DATE(self, mocker, _reload):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, _ = _make_context(mocker, events={ev.id: ev})
        state = _run(_dl_module.get_delete_name(_make_update(mocker, "Riunione"), ctx))
        assert ctx.user_data["delete_name"] == "Riunione"
        assert state == _dl_module.DELETE_DATE

    def test_name_matching_is_case_insensitive(self, mocker, _reload):
        ev = _make_event(mocker, "riunione", _dt())
        ctx, _ = _make_context(mocker, events={ev.id: ev})
        state = _run(_dl_module.get_delete_name(_make_update(mocker, "RIUNIONE"), ctx))
        assert state == _dl_module.DELETE_DATE

    def test_name_is_stripped_before_storage(self, mocker, _reload):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, _ = _make_context(mocker, events={ev.id: ev})
        _run(_dl_module.get_delete_name(_make_update(mocker, "  Riunione  "), ctx))
        assert ctx.user_data["delete_name"] == "Riunione"


# get_delete_date


class TestGetDeleteDate:

    def test_invalid_date_stays_in_DELETE_DATE(self, mocker, _reload):
        _set_parse(None)
        ctx, _ = _make_context(mocker, user_data={"delete_name": "X"})
        state = _run(
            _dl_module.get_delete_date(_make_update(mocker, "non è una data"), ctx)
        )
        assert state == _dl_module.DELETE_DATE

    def test_past_date_rejected(self, mocker, _reload):
        _set_parse(None)
        ctx, _ = _make_context(mocker, user_data={"delete_name": "X"})
        state = _run(
            _dl_module.get_delete_date(_make_update(mocker, "01/01/2000"), ctx)
        )
        assert state == _dl_module.DELETE_DATE

    def test_no_match_on_date_stays_in_DELETE_DATE(self, mocker, _reload):
        target = _dt(month=4, day=28)
        _set_parse(target)
        ev = _make_event(mocker, "Riunione", _dt(month=5, day=1))
        ctx, _ = _make_context(
            mocker,
            user_data={"delete_name": "Riunione"},
            events={ev.id: ev},
        )
        state = _run(
            _dl_module.get_delete_date(_make_update(mocker, "28/04/2099"), ctx)
        )
        assert state == _dl_module.DELETE_DATE

    def test_no_match_reply_mentions_date(self, mocker, _reload):
        target = _dt(month=4, day=28)
        _set_parse(target)
        ev = _make_event(mocker, "Riunione", _dt(month=5, day=1))
        update = _make_update(mocker, "28/04/2099")
        ctx, _ = _make_context(
            mocker,
            user_data={"delete_name": "Riunione"},
            events={ev.id: ev},
        )
        _run(_dl_module.get_delete_date(update, ctx))
        replied = update.message.reply_text.call_args[0][0]
        assert "28/04/2099" in replied

    def test_unique_match_stores_event_id_and_goes_to_DELETE_CONFIRM(
        self, mocker, _reload
    ):
        target = _dt(month=4, day=28, hour=10)
        _set_parse(target)
        ev = _make_event(mocker, "Riunione", target)
        ctx, _ = _make_context(
            mocker,
            user_data={"delete_name": "Riunione"},
            events={ev.id: ev},
        )
        state = _run(
            _dl_module.get_delete_date(_make_update(mocker, "28/04/2099"), ctx)
        )
        assert ctx.user_data["delete_event_id"] == ev.id
        assert state == _dl_module.DELETE_CONFIRM

    def test_multiple_matches_goes_to_DELETE_DISAMBIGUATE(self, mocker, _reload):
        target = _dt(month=4, day=28, hour=10)
        _set_parse(target)
        ev1 = _make_event(mocker, "Riunione", _dt(month=4, day=28, hour=9))
        ev2 = _make_event(mocker, "Riunione", _dt(month=4, day=28, hour=14))
        ctx, _ = _make_context(
            mocker,
            user_data={"delete_name": "Riunione"},
            events={ev1.id: ev1, ev2.id: ev2},
        )
        state = _run(
            _dl_module.get_delete_date(_make_update(mocker, "28/04/2099"), ctx)
        )
        assert state == _dl_module.DELETE_DISAMBIGUATE
        assert len(ctx.user_data["delete_candidates"]) == 2

    def test_multiple_matches_reply_lists_both_events(self, mocker, _reload):
        target = _dt(month=4, day=28, hour=10)
        _set_parse(target)
        ev1 = _make_event(mocker, "Riunione", _dt(month=4, day=28, hour=9))
        ev2 = _make_event(mocker, "Riunione", _dt(month=4, day=28, hour=14))
        update = _make_update(mocker, "28/04/2099")
        ctx, _ = _make_context(
            mocker,
            user_data={"delete_name": "Riunione"},
            events={ev1.id: ev1, ev2.id: ev2},
        )
        _run(_dl_module.get_delete_date(update, ctx))
        replied = update.message.reply_text.call_args[0][0]
        assert "09:00" in replied
        assert "14:00" in replied


# get_delete_disambiguate


class TestGetDeleteDisambiguate:

    def _ctx_with_candidates(self, mocker, ev1, ev2):
        ctx, em = _make_context(
            mocker,
            user_data={"delete_candidates": [ev1.id, ev2.id]},
            events={ev1.id: ev1, ev2.id: ev2},
        )
        return ctx, em

    def test_non_integer_input_stays(self, mocker):
        ev1 = _make_event(mocker, "X", _dt(hour=9))
        ev2 = _make_event(mocker, "X", _dt(hour=14))
        ctx, _ = self._ctx_with_candidates(mocker, ev1, ev2)
        state = _run(
            _dl_module.get_delete_disambiguate(_make_update(mocker, "abc"), ctx)
        )
        assert state == _dl_module.DELETE_DISAMBIGUATE

    def test_out_of_range_stays(self, mocker):
        ev1 = _make_event(mocker, "X", _dt(hour=9))
        ev2 = _make_event(mocker, "X", _dt(hour=14))
        ctx, _ = self._ctx_with_candidates(mocker, ev1, ev2)
        state = _run(_dl_module.get_delete_disambiguate(_make_update(mocker, "5"), ctx))
        assert state == _dl_module.DELETE_DISAMBIGUATE

    def test_zero_stays(self, mocker):
        ev1 = _make_event(mocker, "X", _dt(hour=9))
        ev2 = _make_event(mocker, "X", _dt(hour=14))
        ctx, _ = self._ctx_with_candidates(mocker, ev1, ev2)
        state = _run(_dl_module.get_delete_disambiguate(_make_update(mocker, "0"), ctx))
        assert state == _dl_module.DELETE_DISAMBIGUATE

    def test_valid_choice_stores_event_id_and_goes_to_DELETE_CONFIRM(self, mocker):
        ev1 = _make_event(mocker, "X", _dt(hour=9))
        ev2 = _make_event(mocker, "X", _dt(hour=14))
        ctx, _ = self._ctx_with_candidates(mocker, ev1, ev2)
        state = _run(_dl_module.get_delete_disambiguate(_make_update(mocker, "2"), ctx))
        assert ctx.user_data["delete_event_id"] == ev2.id
        assert state == _dl_module.DELETE_CONFIRM

    def test_choice_1_picks_first_candidate(self, mocker):
        ev1 = _make_event(mocker, "X", _dt(hour=9))
        ev2 = _make_event(mocker, "X", _dt(hour=14))
        ctx, _ = self._ctx_with_candidates(mocker, ev1, ev2)
        _run(_dl_module.get_delete_disambiguate(_make_update(mocker, "1"), ctx))
        assert ctx.user_data["delete_event_id"] == ev1.id


# get_delete_confirm


class TestGetDeleteConfirm:

    def _ctx_with_event(self, mocker, ev):
        ctx, em = _make_context(
            mocker,
            user_data={"delete_event_id": ev.id},
            events={ev.id: ev},
        )
        return ctx, em

    def test_annulla_ends_without_removing(self, mocker):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, em = self._ctx_with_event(mocker, ev)
        state = _run(
            _dl_module.get_delete_confirm(_make_update(mocker, "Annulla"), ctx)
        )
        assert state == ConversationHandler.END
        em.remove_event.assert_not_called()

    def test_invalid_answer_stays_in_DELETE_CONFIRM(self, mocker):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, _ = self._ctx_with_event(mocker, ev)
        state = _run(_dl_module.get_delete_confirm(_make_update(mocker, "forse"), ctx))
        assert state == _dl_module.DELETE_CONFIRM

    def test_conferma_calls_remove_event_with_correct_id(self, mocker):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, em = self._ctx_with_event(mocker, ev)
        _run(_dl_module.get_delete_confirm(_make_update(mocker, "Conferma"), ctx))
        em.remove_event.assert_called_once_with(ev.id, ctx.application)

    def test_conferma_ends_conversation(self, mocker):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, _ = self._ctx_with_event(mocker, ev)
        state = _run(
            _dl_module.get_delete_confirm(_make_update(mocker, "Conferma"), ctx)
        )
        assert state == ConversationHandler.END

    def test_conferma_final_reply_contains_event_name(self, mocker):
        ev = _make_event(mocker, "Riunione", _dt())
        update = _make_update(mocker, "Conferma")
        ctx, _ = self._ctx_with_event(mocker, ev)
        _run(_dl_module.get_delete_confirm(update, ctx))
        final_reply = update.message.reply_text.call_args[0][0]
        assert "Riunione" in final_reply
        assert "eliminato" in final_reply

    def test_show_delete_confirm_contains_event_message(self, mocker):
        """_show_delete_confirm is tested indirectly: get_delete_date calls it
        when it finds a unique match, so we assert on its reply."""
        target = _dt(month=4, day=28, hour=10)
        _set_parse(target)
        ev = _make_event(mocker, "Riunione", target)
        update = _make_update(mocker, "28/04/2099")
        ctx, _ = _make_context(
            mocker,
            user_data={"delete_name": "Riunione"},
            events={ev.id: ev},
        )
        _run(_dl_module.get_delete_date(update, ctx))
        confirm_screen = update.message.reply_text.call_args[0][0]
        assert ev.get_message() in confirm_screen

    def test_event_already_gone_ends_gracefully(self, mocker):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, em = _make_context(
            mocker,
            user_data={"delete_event_id": ev.id},
            events={},
        )
        state = _run(
            _dl_module.get_delete_confirm(_make_update(mocker, "Conferma"), ctx)
        )
        assert state == ConversationHandler.END
        em.remove_event.assert_not_called()

    def test_conferma_calls_append_json_to_expired(self, mocker):
        ev = _make_event(mocker, "Riunione", _dt())
        ctx, _ = self._ctx_with_event(mocker, ev)
        mock_append = mocker.patch.object(_dl_module, "append_json")
        _run(_dl_module.get_delete_confirm(_make_update(mocker, "Conferma"), ctx))
        mock_append.assert_called_once()
        call_args = mock_append.call_args[0]
        assert call_args[0] is ev
        assert call_args[1] == _dl_module.EXPIRED_FILE


# cancel_delete


def test_cancel_delete_is_conversation_logics_cancel():
    """cancel_delete must be the same object as conversation_logics.cancel
    so that its behaviour is already covered by test_conversation_logics."""
    conv = sys.modules["src.modules.conversation_logics"]
    assert _dl_module.cancel_delete is conv.cancel


# delete_event_handler


def test_delete_event_handler_returns_non_none():
    assert _dl_module.delete_event_handler() is not None
