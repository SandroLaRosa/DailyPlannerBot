from __future__ import annotations

from datetime import date
from datetime import datetime as _dt

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.classes.event_manager import EventManager
from src.modules.conversation_logics import _parse_future_dt
from src.modules.timezone_logics import TZ

(RECAP_DATE,) = range(1)


def _events_on_date(em: EventManager, target: date) -> list[str]:
    return [
        ev.get_message() for ev in em.events.values() if ev.start_date.date() == target
    ]


async def start_recap(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message and update.effective_chat and update.effective_user
    await update.message.reply_text(
        "Per quale data vuoi vedere gli eventi?\n(es. 28/04/2026)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return RECAP_DATE


async def get_recap_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message and update.effective_chat and update.effective_user
    assert context.user_data is not None

    parsed = _parse_future_dt(update.message.text or "")
    if parsed is None:
        await update.message.reply_text(
            "Non ho capito la data, riprova.\n"
            "Controlla che sia una data futura!\nUsa il formato: 28/04/2026"
        )
        return RECAP_DATE

    target = parsed.date()
    em: EventManager = context.bot_data["event_manager"]
    matches = _events_on_date(em, target)

    if not matches:
        await update.message.reply_text(
            f"Nessun evento trovato per il {target.strftime('%d/%m/%Y')}."
        )
    else:
        header = f"📅 Eventi del {target.strftime('%d/%m/%Y')}:\n"
        body = "\n\n".join(f"{i}. {msg}" for i, msg in enumerate(matches, start=1))
        await update.message.reply_text(header + body)

    return ConversationHandler.END


async def cancel_recap(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message
    await update.message.reply_text(
        "Recap annullato.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def recap_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("recap", start_recap)],
        states={
            RECAP_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_recap_date)
            ],
        },
        fallbacks=[CommandHandler("annulla", cancel_recap)],
    )


async def today_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia il recap degli eventi di oggi senza chiedere la data."""
    assert update.message and update.effective_chat and update.effective_user

    today = _dt.now(TZ).date()
    em: EventManager = context.bot_data["event_manager"]
    matches = _events_on_date(em, today)

    if not matches:
        await update.message.reply_text(
            f"Nessun evento trovato per oggi ({today.strftime('%d/%m/%Y')})."
        )
    else:
        header = f"📅 Eventi di oggi ({today.strftime('%d/%m/%Y')}):\n"
        body = "\n\n".join(f"{i}. {msg}" for i, msg in enumerate(matches, start=1))
        await update.message.reply_text(header + body)
