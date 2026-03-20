from telegram.ext import Application, CommandHandler, MessageHandler, filters

# TODO: refactor the code in sandrodev to reflect the new handler logics
#       then uncomment the next import:

from modules import command_logics, message_logics #, conversation_logics

# TODO: add new command handlers here as their functions are ready
#       scheme (command, function)
#       reminder: '/' is not needed

COMMAND_HANDLERS = [
    ("start", command_logics.start)
    ("help", command_logics.help)
]

# TODO: add new message handlers here as their functions are ready
#       scheme (filter, function_name)

MESSAGE_HANDLERS = [
    (filters.PHOTO,                             message_logics.photo_handler),
    (filters.AUDIO,                             message_logics.audio_handler),
    (filters.VOICE,                             message_logics.voice_handler),
    (filters.VIDEO,                             message_logics.video_handler),
    (filters.Document.ALL,                      message_logics.document_handler),
    (filters.Sticker.ALL,                       message_logics.sticker_handler),
    (filters.LOCATION,                          message_logics.location_handler),
    (filters.CONTACT,                           message_logics.contact_handler),
    (filters.TEXT & ~filters.COMMAND,           message_logics.plain_text_handler),
    (filters.COMMAND,                           message_logics.unknown_command_handler),
]

# TODO: add new conversation handlers here as their functions are ready
CONVERSATION_HANDLERS = [

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