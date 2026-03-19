from telegram.ext import Application, CommandHandler, MessageHandler, filters

# TODO: refactor the code in sandrodev to reflect the new handler logics
#       then uncomment the next import:
#from modules import command_logics, message_logics, conversation_logics

# TODO: add new command handlers here as their functions are ready
#       scheme (command, function)
#       reminder: '/' is not needed

COMMAND_HANDLERS = [

]

# TODO: add new message handlers here as their functions are ready
#       scheme (filter, function_name)

MESSAGE_HANDLERS = [

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