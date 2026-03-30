from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.modules import (
    command_logics,
    conversation_logics,
    delete_logics,
    message_logics,
    recap_logics,
)

COMMAND_HANDLERS = [
    ("start", command_logics.start),
    ("help", command_logics.help),
    ("today", recap_logics.today_recap),
    ("restart", command_logics.restart),
]

MESSAGE_HANDLERS = [
    (filters.PHOTO, message_logics.photo_handler),
    (filters.AUDIO, message_logics.audio_handler),
    (filters.VOICE, message_logics.voice_handler),
    (filters.VIDEO, message_logics.video_handler),
    (filters.Document.ALL, message_logics.document_handler),
    (filters.Sticker.ALL, message_logics.sticker_handler),
    (filters.LOCATION, message_logics.location_handler),
    (filters.CONTACT, message_logics.contact_handler),
    (filters.TEXT & ~filters.COMMAND, message_logics.plain_text_handler),
    (filters.COMMAND, message_logics.unknown_command_handler),
]

CONVERSATION_HANDLERS = [
    conversation_logics.add_event_handler,
    recap_logics.recap_handler,
    delete_logics.delete_event_handler,
]


def load(app: Application) -> None:

    for build in CONVERSATION_HANDLERS:
        app.add_handler(build())

    for command, handler in COMMAND_HANDLERS:
        app.add_handler(CommandHandler(command, handler))

    for filter_, handler in MESSAGE_HANDLERS:
        app.add_handler(MessageHandler(filter_, handler))


if __name__ == "__main__":
    pass
