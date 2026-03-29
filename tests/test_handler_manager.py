"""
Unit tests for src.modules.handler_manager
"""

from __future__ import annotations

import importlib
import sys

import pytest

import src.modules.handler_manager as _hm_module  # noqa: E402 (stubs injected by fixture)

# Stubs:


@pytest.fixture(autouse=True)
def _stub_modules(mocker):
    stubs = {
        "telegram": mocker.MagicMock(),
        "telegram.ext": mocker.MagicMock(),
        "src.modules.command_logics": mocker.MagicMock(),
        "src.modules.conversation_logics": mocker.MagicMock(),
        "src.modules.message_logics": mocker.MagicMock(),
        "src.modules.lang_logics": mocker.MagicMock(MSG={"unsupported": {}}),
        "src.modules.notify": mocker.MagicMock(),
        "src.modules.timezone_logics": mocker.MagicMock(),
        "src.classes.event_manager": mocker.MagicMock(),
        "src.classes.event": mocker.MagicMock(),
    }
    mocker.patch.dict(sys.modules, stubs)
    importlib.reload(_hm_module)
    yield stubs


# Helpers


def _make_app(mocker):
    app = mocker.MagicMock()
    app.add_handler = mocker.MagicMock()
    return app


# Tests: module lists


class TestHandlerLists:

    def test_conversation_handlers_list_is_non_empty(self):
        assert len(_hm_module.CONVERSATION_HANDLERS) >= 1

    def test_command_handlers_contains_start(self):
        commands = [cmd for cmd, _ in _hm_module.COMMAND_HANDLERS]
        assert "start" in commands

    def test_command_handlers_contains_help(self):
        commands = [cmd for cmd, _ in _hm_module.COMMAND_HANDLERS]
        assert "help" in commands

    def test_command_handlers_contains_restart(self):
        commands = [cmd for cmd, _ in _hm_module.COMMAND_HANDLERS]
        assert "restart" in commands

    def test_message_handlers_list_is_non_empty(self):
        assert len(_hm_module.MESSAGE_HANDLERS) >= 1


# Tests: load


class TestLoad:

    @staticmethod
    def _patch_conv_builders(mocker):
        builders = [mocker.MagicMock() for _ in _hm_module.CONVERSATION_HANDLERS]
        sentinels = [mocker.MagicMock() for _ in builders]
        for builder, sentinel in zip(builders, sentinels):
            builder.return_value = sentinel
        _hm_module.CONVERSATION_HANDLERS = builders
        return builders, sentinels

    def test_load_calls_each_conversation_builder_exactly_once(self, mocker):
        app = _make_app(mocker)
        builders, _ = self._patch_conv_builders(mocker)

        _hm_module.load(app)

        for builder in builders:
            builder.assert_called_once_with()

    def test_load_adds_conversation_handlers_before_command_handlers(self, mocker):
        app = _make_app(mocker)
        _, sentinels = self._patch_conv_builders(mocker)

        _hm_module.load(app)

        first_added = app.add_handler.call_args_list[0][0][0]
        assert first_added is sentinels[0]

    def test_load_passes_built_handler_to_add_handler(self, mocker):
        app = _make_app(mocker)
        _, sentinels = self._patch_conv_builders(mocker)

        _hm_module.load(app)

        for sentinel in sentinels:
            app.add_handler.assert_any_call(sentinel)

    def test_load_total_add_handler_calls_equals_all_handlers(self, mocker):
        app = _make_app(mocker)
        builders, _ = self._patch_conv_builders(mocker)

        _hm_module.load(app)

        expected = (
            len(builders)
            + len(_hm_module.COMMAND_HANDLERS)
            + len(_hm_module.MESSAGE_HANDLERS)
        )
        assert app.add_handler.call_count == expected

    def test_load_uses_command_handler_for_each_command(self, mocker):
        app = _make_app(mocker)
        self._patch_conv_builders(mocker)
        cmd_cls = mocker.patch.object(_hm_module, "CommandHandler")

        _hm_module.load(app)

        assert cmd_cls.call_count == len(_hm_module.COMMAND_HANDLERS)

    def test_load_uses_message_handler_for_each_message_filter(self, mocker):
        app = _make_app(mocker)
        self._patch_conv_builders(mocker)
        msg_cls = mocker.patch.object(_hm_module, "MessageHandler")

        _hm_module.load(app)

        assert msg_cls.call_count == len(_hm_module.MESSAGE_HANDLERS)
