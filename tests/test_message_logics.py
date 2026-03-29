"""
Unit tests for src.modules.command_logics
"""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest

import src.modules.command_logics as _cl_module  # noqa: E402
from tests.stub_helpers import base_stubs

_MSG = {
    "start": {
        "greeting": "Ciao {name}!",
        "checking_missed": "Hai eventi mancati:",
        "missed_item": "- {message}",
        "no_missed": "Nessun evento mancato.",
    },
    "help": {
        "command_list": "Comandi disponibili, {name}.",
    },
    "restart": {
        "begin": "Riavvio in corso...",
        "end": "Riavvio completato.",
    },
}


@pytest.fixture(autouse=True)
def _stub_modules(mocker):
    stubs = base_stubs(mocker)
    stubs["src.modules.timezone_logics"] = mocker.MagicMock()
    stubs["src.modules.lang_logics"] = mocker.MagicMock(MSG=_MSG)
    mocker.patch.dict(sys.modules, stubs)
    importlib.reload(_cl_module)
    yield


def _run(coro):
    return asyncio.run(coro)


def _make_update(mocker, *, chat_id=42):
    update = mocker.MagicMock()
    update.effective_chat = mocker.MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user = mocker.MagicMock()
    update.effective_user.first_name = "Luca"
    update.message = mocker.MagicMock()
    update.message.reply_text = mocker.AsyncMock()
    return update


def _make_context(mocker, *, valid=None, missed=None):
    ctx = mocker.MagicMock()
    em = mocker.MagicMock()
    em.load_ongoing = mocker.MagicMock(return_value=(valid or [], missed or []))
    em.schedule = mocker.MagicMock()
    ctx.bot_data = {"event_manager": em}
    return ctx, em


# Tests: start


class TestStart:

    def test_stores_chat_id_in_bot_data(self, mocker):
        update = _make_update(mocker, chat_id=99)
        ctx, _ = _make_context(mocker)
        _run(_cl_module.start(update, ctx))
        assert ctx.bot_data["chat_id"] == 99

    def test_chat_id_none_returns_early_no_reply(self, mocker):
        update = _make_update(mocker, chat_id=None)
        ctx, _ = _make_context(mocker)
        update.effective_chat.id = None
        _run(_cl_module.start(update, ctx))
        update.message.reply_text.assert_not_awaited()

    def test_sends_greeting_with_name(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker)
        _run(_cl_module.start(update, ctx))
        first_text = update.message.reply_text.call_args_list[0][0][0]
        assert "Luca" in first_text

    def test_no_missed_sends_no_missed_message(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker, valid=[], missed=[])
        _run(_cl_module.start(update, ctx))
        texts = [call[0][0] for call in update.message.reply_text.call_args_list]
        assert _MSG["start"]["no_missed"] in texts

    def test_no_missed_does_not_send_checking_missed(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker, valid=[], missed=[])
        _run(_cl_module.start(update, ctx))
        texts = [call[0][0] for call in update.message.reply_text.call_args_list]
        assert not any(_MSG["start"]["checking_missed"] in t for t in texts)

    def test_with_missed_sends_missed_block(self, mocker):
        ev = mocker.MagicMock()
        ev.get_message = mocker.MagicMock(return_value="Evento mancato")
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker, missed=[ev])
        _run(_cl_module.start(update, ctx))
        texts = [call[0][0] for call in update.message.reply_text.call_args_list]
        assert any(_MSG["start"]["checking_missed"] in t for t in texts)
        assert any("Evento mancato" in t for t in texts)

    def test_missed_does_not_send_no_missed_message(self, mocker):
        ev = mocker.MagicMock()
        ev.get_message = mocker.MagicMock(return_value="X")
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker, missed=[ev])
        _run(_cl_module.start(update, ctx))
        texts = [call[0][0] for call in update.message.reply_text.call_args_list]
        assert _MSG["start"]["no_missed"] not in texts

    def test_with_valid_schedules_each_event(self, mocker):
        ev1 = mocker.MagicMock()
        ev2 = mocker.MagicMock()
        update = _make_update(mocker)
        ctx, em = _make_context(mocker, valid=[ev1, ev2])
        _run(_cl_module.start(update, ctx))
        assert em.schedule.call_count == 2


# Tests: help


class TestHelp:

    def test_sends_command_list_with_name(self, mocker):
        update = _make_update(mocker)
        ctx = mocker.MagicMock()
        _run(_cl_module.help(update, ctx))
        update.message.reply_text.assert_awaited_once()
        assert "Luca" in update.message.reply_text.call_args[0][0]

    def test_sends_exactly_one_message(self, mocker):
        update = _make_update(mocker)
        _run(_cl_module.help(update, mocker.MagicMock()))
        assert update.message.reply_text.await_count == 1


# Tests: restart


class TestRestart:

    def test_sends_begin_message(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker)
        mocker.patch.object(_cl_module, "start", new=mocker.AsyncMock())
        _run(_cl_module.restart(update, ctx))
        texts = [call[0][0] for call in update.message.reply_text.call_args_list]
        assert _MSG["restart"]["begin"] in texts

    def test_sends_end_message(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker)
        mocker.patch.object(_cl_module, "start", new=mocker.AsyncMock())
        _run(_cl_module.restart(update, ctx))
        texts = [call[0][0] for call in update.message.reply_text.call_args_list]
        assert _MSG["restart"]["end"] in texts

    def test_calls_start_exactly_once_with_correct_args(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker)
        mock_start = mocker.patch.object(_cl_module, "start", new=mocker.AsyncMock())
        _run(_cl_module.restart(update, ctx))
        mock_start.assert_awaited_once_with(update, ctx)

    def test_begin_sent_before_end(self, mocker):
        update = _make_update(mocker)
        ctx, _ = _make_context(mocker)
        mocker.patch.object(_cl_module, "start", new=mocker.AsyncMock())
        _run(_cl_module.restart(update, ctx))
        calls = [c[0][0] for c in update.message.reply_text.call_args_list]
        assert calls.index(_MSG["restart"]["begin"]) < calls.index(
            _MSG["restart"]["end"]
        )
