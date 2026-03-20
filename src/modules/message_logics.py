from telegram import Update
from telegram.ext import ContextTypes


# Text 

async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Hai scritto: \\{update.message.text}.\n"
        "Non conosco comandi corrispondenti.\n"
        "Per una lista dei comandi disponibili consulta /help."
    )

async def plain_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Non sono ancora in grado di elaborare messaggi.\n"
        "Usa uno dei comandi disponibili. Per la lista consulta /help."
    )

# Media

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente l'invio di immagini.")

async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente l'invio di audio.")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente i messaggi vocali.")

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente l'invio di video.")

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente l'invio di documenti.")

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente gli sticker.")

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente la condivisione di posizione.")

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Il bot non supporta attualmente la condivisione di contatti.")


if __name__ == "__main__":
    pass