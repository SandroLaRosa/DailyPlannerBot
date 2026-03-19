import os
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application

#from modules import handler-loader    <- codice già scritto in sandrodev, ma da pulire

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def main()->None:
    load_dotenv()
    token= os.getenv("TOKEN")
    if not token:
        logger.critical("TOKEN not found. Please verify that your .env file has been properly created.")
        raise ValueError("Missing Telegram bot Token.")
    app=Application.builder().token(token).build()

    # TODO:     Refactor the event_manager code in sandrodev branch which is not currently working
    #           once the implementation is stable insert its logic here to ensure that the bot and
    #           the event manager can properly interact.

    # TODO v2:  Refactor the handlers and their loader
    #           here we shall have code like:
    #           handlers.load(app)

    logger.info("Bot started successfully. Polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()