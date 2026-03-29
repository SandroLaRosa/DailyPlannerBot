def base_stubs(mocker):
    return {
        "telegram": mocker.MagicMock(),
        "telegram.ext": mocker.MagicMock(),
        "src.classes.event_manager": mocker.MagicMock(),
        "src.classes.event": mocker.MagicMock(),
        "src.modules.notify": mocker.MagicMock(notify_event=mocker.AsyncMock()),
    }
