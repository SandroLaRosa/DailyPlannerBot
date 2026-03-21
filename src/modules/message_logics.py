from telegram import Update
from telegram.ext import ContextTypes

from modules.lang_logics import MSG

DIC = MSG["unsupported"]

# Text

async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        DIC["unknown_command"].format(command=update.message.text)
    )

async def plain_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["plain_text"])

# Media

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["photo"])

async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["audio"])

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["voice"])

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["video"])

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["document"])

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["sticker"])

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["location"])

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(DIC["contact"])

if __name__ == "__main__":
    pass