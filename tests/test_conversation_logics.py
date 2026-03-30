"""
Unit tests for src.modules.conversation_logics
"""

from __future__ import annotations

import asyncio
import sys
import unittest.mock as _umock
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta
from telegram.ext import ConversationHandler

from src.modules import conversation_logics as cl  # noqa: E402
from src.modules.conversation_logics import (  # noqa: E402
    PERIOD_MAP,
    _format_period,
    _is_no,
    _is_yes,
    _parse_duration,
    _parse_future_dt,
    _text,
    _user_data,
    add_event_handler,
    cancel,
    get_confirm,
    get_custom_period,
    get_description,
    get_end_date,
    get_event_type,
    get_frequency,
    get_has_description,
    get_name,
    get_period,
    get_start_date,
    show_recap,
    start_event_creation,
)
from tests.stub_helpers import make_update as _make_update


# Stub
def _make_stub(mocker):
    return mocker.MagicMock()


_telegram_stub = _umock.MagicMock()
sys.modules.setdefault("telegram", _telegram_stub)
sys.modules.setdefault("telegram.ext", _telegram_stub)

_notify_stub = _umock.MagicMock()
_notify_stub.notify_event = _umock.AsyncMock()
sys.modules.setdefault("src.modules.notify", _notify_stub)

sys.modules.setdefault("src.classes.event_manager", _umock.MagicMock())
sys.modules.setdefault("src.classes.event", _umock.MagicMock())

_tz_stub = _umock.MagicMock()
_tz_stub.TZ = ZoneInfo("Europe/Rome")
sys.modules.setdefault("src.modules.timezone_logics", _tz_stub)


_TZ = ZoneInfo("Europe/Rome")

# Helpers


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _make_context(mocker, user_data: dict | None = None, bot_data: dict | None = None):
    ctx = mocker.MagicMock()
    ctx.user_data = user_data if user_data is not None else {}
    ctx.bot_data = bot_data if bot_data is not None else {}
    return ctx


def _future_dt(year: int = 2099, hour: int = 10) -> datetime:
    return datetime(year, 1, 1, hour, 0, tzinfo=_TZ)


def _make_em(mocker):
    em = mocker.MagicMock()
    em.add_event = mocker.MagicMock()
    return em


def _single_user_data(event_type: str = "single") -> dict:
    d: dict = {
        "event_type": event_type,
        "name": "Test",
        "start_date": _future_dt(2099, 10),
        "description": "desc",
    }
    if event_type != "reminder":
        d["end_date"] = _future_dt(2099, 12)
    if event_type == "recurring":
        d["period"] = relativedelta(weeks=1)
        d["freq"] = 3
    return d


@pytest.mark.parametrize("word", ["sì", "si", "yes", "yep"])
def test_is_yes_truthy(word):
    assert _is_yes(word) is True


def test_is_yes_falsy():
    assert _is_yes("no") is False


@pytest.mark.parametrize("word", ["no", "nope"])
def test_is_no_truthy(word):
    assert _is_no(word) is True


def test_is_no_falsy():
    assert _is_no("sì") is False


def test_text_returns_message_text(mocker):
    assert _text(_make_update(mocker, "ciao")) == "ciao"


def test_text_raises_when_message_is_none(mocker):
    update = mocker.MagicMock()
    update.message = None
    with pytest.raises(AssertionError):
        _text(update)


def test_text_raises_when_text_is_none(mocker):
    update = mocker.MagicMock()
    update.message.text = None
    with pytest.raises(AssertionError):
        _text(update)


def test_user_data_returns_dict(mocker):
    ctx = _make_context(mocker, user_data={"k": "v"})
    assert _user_data(ctx) == {"k": "v"}


def test_user_data_raises_when_none(mocker):
    ctx = mocker.MagicMock()
    ctx.user_data = None
    with pytest.raises(AssertionError):
        _user_data(ctx)


def test_parse_future_dt_valid():
    dt = _parse_future_dt("01/01/2099 10:00")
    assert dt is not None and dt.year == 2099


def test_parse_future_dt_past_returns_none():
    assert _parse_future_dt("01/01/2000 10:00") is None


def test_parse_future_dt_garbage_returns_none():
    assert _parse_future_dt("non è una data!!!") is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1 anno", relativedelta(years=1)),
        ("2 anni", relativedelta(years=2)),
        ("1 mese", relativedelta(months=1)),
        ("3 mesi", relativedelta(months=3)),
        ("1 settimana", relativedelta(weeks=1)),
        ("2 settimane", relativedelta(weeks=2)),
        ("1 giorno", relativedelta(days=1)),
        ("5 giorni", relativedelta(days=5)),
        ("1 ora", relativedelta(hours=1)),
        ("2 ore", relativedelta(hours=2)),
        ("1 minuto", relativedelta(minutes=1)),
        ("30 minuti", relativedelta(minutes=30)),
        ("1 secondo", relativedelta(seconds=1)),
        ("10 secondi", relativedelta(seconds=10)),
    ],
)
def test_parse_duration_unit_mappings(text, expected):
    assert _parse_duration(text) == expected


def test_parse_duration_multiple_units():
    result = _parse_duration(
        "1 anno 2 mesi 3 settimane 4 giorni 5 ore 6 minuti 7 secondi"
    )
    assert result == relativedelta(
        years=1, months=2, weeks=3, days=4, hours=5, minutes=6, seconds=7
    )


def test_parse_duration_accumulates_same_unit():
    assert _parse_duration("2 giorni 3 giorni") == relativedelta(days=5)


def test_parse_duration_no_match_returns_none():
    assert _parse_duration("nessun numero qui") is None


def test_format_period_empty_returns_dash():
    assert _format_period(relativedelta()) == "—"


@pytest.mark.parametrize(
    "rd,expected_word",
    [
        (relativedelta(years=1), "anno"),
        (relativedelta(years=2), "anni"),
        (relativedelta(months=1), "mese"),
        (relativedelta(months=2), "mesi"),
        (relativedelta(days=1), "giorno"),
        (relativedelta(days=3), "giorni"),
        (relativedelta(hours=1), "ora"),
        (relativedelta(hours=2), "ore"),
        (relativedelta(minutes=1), "minuto"),
        (relativedelta(minutes=5), "minuti"),
    ],
)
def test_format_period_singular_and_plural(rd, expected_word):
    assert expected_word in _format_period(rd)


def test_format_period_combined():
    rd = relativedelta(years=1, months=2, days=3, hours=4, minutes=5)
    result = _format_period(rd)
    for word in ("anno", "mesi", "giorni", "ore", "minuti"):
        assert word in result


def test_start_event_creation_clears_user_data_returns_NAME(mocker):
    update = _make_update(mocker)
    ctx = _make_context(mocker, user_data={"stale_key": True})
    state = _run(start_event_creation(update, ctx))
    assert ctx.user_data == {}
    assert state == cl.NAME
    update.message.reply_text.assert_awaited_once()


def test_get_name_strips_and_stores_returns_EVENT_TYPE(mocker):
    update = _make_update(mocker, "  Riunione  ")
    ctx = _make_context(mocker)
    state = _run(get_name(update, ctx))
    assert ctx.user_data["name"] == "Riunione"
    assert state == cl.EVENT_TYPE


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ("Evento", "single"),
        ("Evento ricorrente", "recurring"),
        ("Promemoria", "reminder"),
    ],
)
def test_get_event_type_valid_advances_to_START_DATE(mocker, text, expected_type):
    ctx = _make_context(mocker)
    state = _run(get_event_type(_make_update(mocker, text), ctx))
    assert ctx.user_data["event_type"] == expected_type
    assert state == cl.START_DATE


def test_get_event_type_invalid_stays(mocker):
    state = _run(get_event_type(_make_update(mocker, "banana"), _make_context(mocker)))
    assert state == cl.EVENT_TYPE


def test_get_start_date_invalid_stays(mocker):
    ctx = _make_context(mocker, user_data={"event_type": "single"})
    assert (
        _run(get_start_date(_make_update(mocker, "not a date"), ctx)) == cl.START_DATE
    )


def test_get_start_date_single_goes_to_END_DATE(mocker):
    ctx = _make_context(mocker, user_data={"event_type": "single"})
    state = _run(get_start_date(_make_update(mocker, "01/01/2099 10:00"), ctx))
    assert state == cl.END_DATE
    assert "start_date" in ctx.user_data


def test_get_start_date_reminder_goes_to_DESCRIPTION(mocker):
    ctx = _make_context(mocker, user_data={"event_type": "reminder"})
    state = _run(get_start_date(_make_update(mocker, "01/01/2099 10:00"), ctx))
    assert state == cl.DESCRIPTION


def test_get_end_date_invalid_stays(mocker):
    ctx = _make_context(mocker, user_data={"start_date": _future_dt()})
    assert _run(get_end_date(_make_update(mocker, "not a date"), ctx)) == cl.END_DATE


def test_get_end_date_before_start_stays(mocker):
    ctx = _make_context(mocker, user_data={"start_date": _future_dt(2099)})
    assert (
        _run(get_end_date(_make_update(mocker, "01/01/2090 10:00"), ctx)) == cl.END_DATE
    )


def test_get_end_date_valid_advances_to_HAS_DESCRIPTION(mocker):
    ctx = _make_context(mocker, user_data={"start_date": _future_dt(2099, hour=10)})
    state = _run(get_end_date(_make_update(mocker, "01/01/2099 12:00"), ctx))
    assert state == cl.HAS_DESCRIPTION
    assert "end_date" in ctx.user_data


def test_get_has_description_no_single_goes_to_CONFIRM(mocker):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "single",
            "name": "X",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_has_description(_make_update(mocker, "No"), ctx))
    assert ctx.user_data["description"] is None
    assert state == cl.CONFIRM


def test_get_has_description_no_recurring_goes_to_FREQ(mocker):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "recurring",
            "name": "X",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_has_description(_make_update(mocker, "No"), ctx))
    assert state == cl.FREQ


def test_get_has_description_yes_goes_to_DESCRIPTION(mocker):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "single",
            "name": "X",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_has_description(_make_update(mocker, "Sì"), ctx))
    assert state == cl.DESCRIPTION


def test_get_has_description_invalid_stays(mocker):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "single",
            "name": "X",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_has_description(_make_update(mocker, "boh"), ctx))
    assert state == cl.HAS_DESCRIPTION


def test_get_description_single_stores_and_goes_to_CONFIRM(mocker):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "single",
            "name": "X",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_description(_make_update(mocker, "  la mia nota  "), ctx))
    assert ctx.user_data["description"] == "la mia nota"
    assert state == cl.CONFIRM


def test_get_description_recurring_goes_to_FREQ(mocker):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "recurring",
            "name": "X",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_description(_make_update(mocker, "una nota"), ctx))
    assert state == cl.FREQ


def test_get_frequency_non_integer_stays(mocker):
    assert (
        _run(get_frequency(_make_update(mocker, "abc"), _make_context(mocker)))
        == cl.FREQ
    )


def test_get_frequency_zero_stays(mocker):
    assert (
        _run(get_frequency(_make_update(mocker, "0"), _make_context(mocker))) == cl.FREQ
    )


def test_get_frequency_negative_stays(mocker):
    assert (
        _run(get_frequency(_make_update(mocker, "-3"), _make_context(mocker)))
        == cl.FREQ
    )


def test_get_frequency_valid_stores_and_goes_to_PERIOD(mocker):
    ctx = _make_context(mocker)
    state = _run(get_frequency(_make_update(mocker, "5"), ctx))
    assert ctx.user_data["freq"] == 5
    assert state == cl.PERIOD


@pytest.mark.parametrize("period_text", list(PERIOD_MAP.keys()))
def test_get_period_valid_stores_and_goes_to_CONFIRM(mocker, period_text):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "recurring",
            "name": "X",
            "freq": 2,
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_period(_make_update(mocker, period_text), ctx))
    assert ctx.user_data["period"] == PERIOD_MAP[period_text]
    assert state == cl.CONFIRM


def test_get_period_custom_goes_to_CUSTOM_PERIOD(mocker):
    state = _run(get_period(_make_update(mocker, "custom"), _make_context(mocker)))
    assert state == cl.CUSTOM_PERIOD


def test_get_period_invalid_stays(mocker):
    state = _run(get_period(_make_update(mocker, "trimestrale"), _make_context(mocker)))
    assert state == cl.PERIOD


def test_get_custom_period_invalid_stays(mocker):
    state = _run(
        get_custom_period(_make_update(mocker, "ogni tanto"), _make_context(mocker))
    )
    assert state == cl.CUSTOM_PERIOD


def test_get_custom_period_valid_stores_and_goes_to_CONFIRM(mocker):
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "recurring",
            "name": "X",
            "freq": 2,
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
        },
    )
    state = _run(get_custom_period(_make_update(mocker, "10 giorni"), ctx))
    assert ctx.user_data["period"] == relativedelta(days=10)
    assert state == cl.CONFIRM


def test_show_recap_single_contains_name_returns_CONFIRM(mocker):
    update = _make_update(mocker)
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "single",
            "name": "Meeting",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
            "description": "note",
        },
    )
    state = _run(show_recap(update, ctx))
    assert state == cl.CONFIRM
    assert "Meeting" in update.message.reply_text.call_args[0][0]


def test_show_recap_reminder_returns_CONFIRM(mocker):
    update = _make_update(mocker)
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "reminder",
            "name": "Pillola",
            "start_date": _future_dt(2099, 8),
            "description": "prendere la pillola",
        },
    )
    assert _run(show_recap(update, ctx)) == cl.CONFIRM


def test_show_recap_recurring_shows_freq(mocker):
    update = _make_update(mocker)
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "recurring",
            "name": "Stand-up",
            "freq": 7,
            "period": relativedelta(weeks=1),
            "start_date": _future_dt(2099, 9),
            "end_date": _future_dt(2099, 10),
            "description": None,
        },
    )
    state = _run(show_recap(update, ctx))
    assert state == cl.CONFIRM
    assert "7" in update.message.reply_text.call_args[0][0]


def test_show_recap_no_description_shows_dash(mocker):
    update = _make_update(mocker)
    ctx = _make_context(
        mocker,
        user_data={
            "event_type": "single",
            "name": "X",
            "start_date": _future_dt(2099, 10),
            "end_date": _future_dt(2099, 12),
            "description": None,
        },
    )
    _run(show_recap(update, ctx))
    assert "—" in update.message.reply_text.call_args[0][0]


def test_get_confirm_annulla_ends_conversation(mocker):

    ctx = _make_context(mocker, user_data=_single_user_data("single"))
    state = _run(get_confirm(_make_update(mocker, "cancel"), ctx))
    assert state == ConversationHandler.END


def test_get_confirm_invalid_stays_in_CONFIRM(mocker):
    ctx = _make_context(mocker, user_data=_single_user_data("single"))
    assert _run(get_confirm(_make_update(mocker, "forse"), ctx)) == cl.CONFIRM


def test_get_confirm_single_creates_event_and_ends(mocker):

    em = _make_em(mocker)
    ctx = _make_context(
        mocker, user_data=_single_user_data("single"), bot_data={"event_manager": em}
    )
    assert (
        _run(get_confirm(_make_update(mocker, "confirm"), ctx))
        == ConversationHandler.END
    )
    em.add_event.assert_called_once()


def test_get_confirm_recurring_creates_event_and_ends(mocker):

    em = _make_em(mocker)
    ctx = _make_context(
        mocker, user_data=_single_user_data("recurring"), bot_data={"event_manager": em}
    )
    assert (
        _run(get_confirm(_make_update(mocker, "confirm"), ctx))
        == ConversationHandler.END
    )
    em.add_event.assert_called_once()


def test_get_confirm_reminder_creates_event_and_ends(mocker):

    em = _make_em(mocker)
    ctx = _make_context(
        mocker, user_data=_single_user_data("reminder"), bot_data={"event_manager": em}
    )
    assert (
        _run(get_confirm(_make_update(mocker, "confirm"), ctx))
        == ConversationHandler.END
    )
    em.add_event.assert_called_once()


def test_cancel_ends_conversation_and_replies(mocker):

    update = _make_update(mocker)
    state = _run(cancel(update, _make_context(mocker)))
    assert state == ConversationHandler.END
    update.message.reply_text.assert_awaited_once()


def test_add_event_handler_returns_non_none():
    assert add_event_handler() is not None
