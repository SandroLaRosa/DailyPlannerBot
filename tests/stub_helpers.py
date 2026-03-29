def base_stubs(mocker):
    return {
        "telegram": mocker.MagicMock(),
        "telegram.ext": mocker.MagicMock(),
        "src.classes.event_manager": mocker.MagicMock(),
        "src.classes.event": mocker.MagicMock(),
        "src.modules.notify": mocker.MagicMock(notify_event=mocker.AsyncMock()),
    }


def make_update(mocker, text: str = "placeholder"):
    update = mocker.MagicMock()
    update.effective_chat = mocker.MagicMock()
    update.effective_user = mocker.MagicMock()
    update.effective_user.first_name = "Luca"
    update.message = mocker.MagicMock()
    update.message.text = text
    update.message.reply_text = mocker.AsyncMock()
    return update
