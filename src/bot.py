"""DailyPlannerBot entry point"""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application

from classes.event_manager import EventManager
from modules.handler_manager import load

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the Bot and start logging its states"""
    token = os.getenv("TOKEN")
    if not token:
        logger.critical("TOKEN not found. Please check your .env file.")
        raise ValueError("Missing Telegram bot Token.")
    app = Application.builder().token(token).build()
    app.bot_data["event_manager"] = EventManager()
    load(app)

    logger.info("Bot started successfully. Polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
