"""Unit tests for src.modules.recap_logics"""

from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from telegram.ext import ConversationHandler

import src.modules.recap_logics as _rl_module
from tests.stub_helpers import base_stubs

_TZ = ZoneInfo("Europe/Rome")


@pytest.fixture(autouse=True)
def _stub_modules(mocker):
    stubs = base_stubs(mocker)
    stubs["src.modules.timezone_logics"] = mocker.MagicMock(TZ=_TZ)
    stubs["src.modules.conversation_logics"] = mocker.MagicMock(
        _parse_future_dt=mocker.MagicMock()
    )
    stubs["telegram.ext"].ConversationHandler.END = -1
    mocker.patch.dict(sys.modules, stubs)
    importlib.reload(_rl_module)
    yield stubs


def _run(coro):
    return asyncio.run(coro)


def _make_update(mocker, text: str = "28/04/2099"):
    update = mocker.MagicMock()
    update.effective_chat = mocker.MagicMock()
    update.effective_user = mocker.MagicMock()
    update.message = mocker.MagicMock()
    update.message.text = text
    update.message.reply_text = mocker.AsyncMock()
    return update


def _make_context(mocker, events: dict | None = None):
    ctx = mocker.MagicMock()
    ctx.user_data = {}
    em = mocker.MagicMock()
    em.events = events or {}
    ctx.bot_data = {"event_manager": em}
    return ctx


def _make_event(mocker, start: datetime):
    ev = mocker.MagicMock()
    ev.start_date = start
    ev.get_message = mocker.MagicMock(
        return_value=f"Evento alle {start.strftime('%H:%M')}"
    )
    return ev


def _set_parse(stubs, return_value):
    # pylint: disable=protected-access
    stubs["src.modules.conversation_logics"]._parse_future_dt.return_value = (
        return_value
    )


def test_start_recap_replies_and_returns_RECAP_DATE(mocker, _stub_modules):
    update = _make_update(mocker)
    state = _run(_rl_module.start_recap(update, _make_context(mocker)))
    assert state == _rl_module.RECAP_DATE
    update.message.reply_text.assert_awaited_once()


def test_get_recap_date_invalid_stays(mocker, _stub_modules):
    _set_parse(_stub_modules, None)
    update = _make_update(mocker, "non è una data")
    state = _run(_rl_module.get_recap_date(update, _make_context(mocker)))
    assert state == _rl_module.RECAP_DATE


def test_get_recap_date_past_date_rejected(mocker, _stub_modules):
    _set_parse(_stub_modules, None)
    update = _make_update(mocker, "01/01/2020")
    state = _run(_rl_module.get_recap_date(update, _make_context(mocker)))
    assert state == _rl_module.RECAP_DATE
    replied = update.message.reply_text.call_args[0][0]
    assert "futura" in replied


def test_get_recap_date_no_events_replies_none_found(mocker, _stub_modules):
    _set_parse(_stub_modules, datetime(2099, 4, 28, 10, 0, tzinfo=_TZ))
    update = _make_update(mocker, "28/04/2099")
    state = _run(_rl_module.get_recap_date(update, _make_context(mocker, events={})))
    assert state == ConversationHandler.END
    replied = update.message.reply_text.call_args[0][0]
    assert "Nessun evento" in replied


def test_get_recap_date_matching_event_appears_in_reply(mocker, _stub_modules):
    target = datetime(2099, 4, 28, 10, 0, tzinfo=_TZ)
    _set_parse(_stub_modules, target)
    ev = _make_event(mocker, target)
    ctx = _make_context(mocker, events={"id-1": ev})
    update = _make_update(mocker, "28/04/2099")
    state = _run(_rl_module.get_recap_date(update, ctx))
    assert state == ConversationHandler.END
    replied = update.message.reply_text.call_args[0][0]
    assert "10:00" in replied


def test_get_recap_date_filters_out_other_dates(mocker, _stub_modules):
    same_day = datetime(2099, 4, 28, 9, 0, tzinfo=_TZ)
    other_day = datetime(2099, 5, 1, 9, 0, tzinfo=_TZ)
    _set_parse(_stub_modules, same_day)
    events = {
        "a": _make_event(mocker, same_day),
        "b": _make_event(mocker, other_day),
    }
    ctx = _make_context(mocker, events=events)
    update = _make_update(mocker, "28/04/2099")
    _run(_rl_module.get_recap_date(update, ctx))
    replied = update.message.reply_text.call_args[0][0]
    assert "09:00" in replied
    assert "05/2099" not in replied


def test_get_recap_date_multiple_events_all_listed(mocker, _stub_modules):
    base = datetime(2099, 4, 28, 8, 0, tzinfo=_TZ)
    _set_parse(_stub_modules, base)
    ev1 = _make_event(mocker, datetime(2099, 4, 28, 8, 0, tzinfo=_TZ))
    ev2 = _make_event(mocker, datetime(2099, 4, 28, 14, 0, tzinfo=_TZ))
    ctx = _make_context(mocker, events={"a": ev1, "b": ev2})
    update = _make_update(mocker, "28/04/2099")
    _run(_rl_module.get_recap_date(update, ctx))
    replied = update.message.reply_text.call_args[0][0]
    assert "08:00" in replied
    assert "14:00" in replied


def test_cancel_recap_ends_and_replies(mocker, _stub_modules):
    update = _make_update(mocker)
    state = _run(_rl_module.cancel_recap(update, _make_context(mocker)))
    assert state == ConversationHandler.END
    update.message.reply_text.assert_awaited_once()


def test_recap_handler_returns_non_none(_stub_modules):
    assert _rl_module.recap_handler() is not None
