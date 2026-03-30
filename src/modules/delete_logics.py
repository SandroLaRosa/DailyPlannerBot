from __future__ import annotations

from datetime import date

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.classes.event import Event
from src.classes.event_manager import EXPIRED_FILE, EventManager, append_json
from src.modules.conversation_logics import (  # noqa: PLC0415
    _parse_future_dt as _parse_dt,
)
from src.modules.conversation_logics import cancel as cancel_delete


def parse_future_dt(text: str):
    """Public wrapper around conversation_logics._parse_future_dt."""
    return _parse_dt(text)


# States
(
    DELETE_NAME,
    DELETE_DATE,
    DELETE_DISAMBIGUATE,
    DELETE_CONFIRM,
) = range(4)

_CONFIRM_KEY = ReplyKeyboardMarkup(
    [["confirm", "cancel"]],
    one_time_keyboard=True,
    resize_keyboard=True,
)


# helpers:


def _matches_by_name(em: EventManager, name: str) -> list[Event]:
    """Return every active event whose name matches case-insensitively."""
    needle = name.strip().lower()
    return [ev for ev in em.events.values() if ev.name.lower() == needle]


def _matches_by_name_and_date(em: EventManager, name: str, day: date) -> list[Event]:
    """Narrow down to events matching both name and start day."""
    return [ev for ev in _matches_by_name(em, name) if ev.start_date.date() == day]


def _event_summary(ev: Event) -> str:
    return (
        f"• {ev.name}  —  {ev.start_date.strftime('%d/%m/%Y %H:%M')}\n"
        f"  {ev.get_message()}"
    )


def _store(context: ContextTypes.DEFAULT_TYPE, **kwargs) -> None:
    assert context.user_data is not None
    context.user_data.update(kwargs)


def _ud(context: ContextTypes.DEFAULT_TYPE) -> dict:
    assert context.user_data is not None
    return context.user_data


def _text(update: Update) -> str:
    assert update.message is not None and update.message.text is not None
    return update.message.text


# entry point


async def start_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message and update.effective_chat and update.effective_user
    _ud(context).clear()
    await update.message.reply_text(
        "Qual è il nome dell'evento che vuoi eliminare?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DELETE_NAME


# step 1: get_name


async def get_delete_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message and update.effective_chat and update.effective_user
    name = _text(update).strip()

    em: EventManager = context.bot_data["event_manager"]
    candidates = _matches_by_name(em, name)

    if not candidates:
        await update.message.reply_text(
            f'Nessun evento con nome "{name}" trovato.\n'
            "Riprova con un altro nome, oppure /annulla per uscire."
        )
        return DELETE_NAME

    _store(context, delete_name=name)
    await update.message.reply_text(
        f"Trovati {len(candidates)} evento/i con questo nome.\n"
        "Per quale data? (es. 28/04/2026)"
    )
    return DELETE_DATE


# step 2A: get_date


async def get_delete_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message and update.effective_chat and update.effective_user

    parsed = parse_future_dt(_text(update))
    if parsed is None:
        await update.message.reply_text(
            "Non ho capito la data, riprova.\n"
            "Controlla che sia una data futura! Usa il formato: 28/04/2026"
        )
        return DELETE_DATE

    day = parsed.date()
    em: EventManager = context.bot_data["event_manager"]
    name: str = _ud(context)["delete_name"]
    matches = _matches_by_name_and_date(em, name, day)

    if not matches:
        await update.message.reply_text(
            f"Nessun evento \"{name}\" trovato il {day.strftime('%d/%m/%Y')}.\n"
            "Prova con un'altra data, oppure /annulla per uscire."
        )
        return DELETE_DATE

    if len(matches) == 1:
        _store(context, delete_event_id=matches[0].id)
        return await _show_delete_confirm(update, context, matches[0])

    _store(context, delete_candidates=[ev.id for ev in matches])
    lines = ["Più eventi trovati in quella data, scegli il numero:\n"]
    for i, ev in enumerate(matches, start=1):
        lines.append(f"{i}. {ev.start_date.strftime('%H:%M')}  {ev.name}")
        if ev.description:
            lines.append(f"   {ev.description}")
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=ReplyKeyboardMarkup(
            [[str(i) for i in range(1, len(matches) + 1)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return DELETE_DISAMBIGUATE


# step 2b: resolve_disambiguation


async def get_delete_disambiguate(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    assert update.message and update.effective_chat and update.effective_user

    candidates: list[str] = _ud(context)["delete_candidates"]
    try:
        choice = int(_text(update).strip())
        if not 1 <= choice <= len(candidates):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            f"Inserisci un numero tra 1 e {len(candidates)}."
        )
        return DELETE_DISAMBIGUATE

    em: EventManager = context.bot_data["event_manager"]
    event_id = candidates[choice - 1]
    event = em.events[event_id]
    _store(context, delete_event_id=event_id)
    return await _show_delete_confirm(update, context, event)


# confirm screen


async def _show_delete_confirm(
    update: Update, _context: ContextTypes.DEFAULT_TYPE, event: Event
) -> int:
    assert update.message
    lines = [
        "⚠️ Vuoi eliminare questo evento?\n",
        _event_summary(event),
        "\nConfirm per eliminare, Cancel per tornare indietro.",
    ]
    await update.message.reply_text("\n".join(lines), reply_markup=_CONFIRM_KEY)
    return DELETE_CONFIRM


# step 3: confirm


async def get_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message and update.effective_chat and update.effective_user
    answer = _text(update).strip().lower()

    if "cancel" in answer:
        await update.message.reply_text(
            "Eliminazione annullata.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if "confirm" not in answer:
        await update.message.reply_text(
            "Scegli Confirm o Cancel.", reply_markup=_CONFIRM_KEY
        )
        return DELETE_CONFIRM

    em: EventManager = context.bot_data["event_manager"]
    event_id: str = _ud(context)["delete_event_id"]
    event = em.events.get(event_id)

    if event is None:
        # Race condition: already gone
        await update.message.reply_text(
            "Evento non più disponibile (già eliminato?).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    append_json(event, EXPIRED_FILE)
    em.remove_event(event_id, context.application)

    await update.message.reply_text(
        f'✅ Evento "{event.name}" del '
        f"{event.start_date.strftime('%d/%m/%Y %H:%M')} eliminato.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# handler factory


def delete_event_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("delete", start_delete)],
        states={
            DELETE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_delete_name)
            ],
            DELETE_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_delete_date)
            ],
            DELETE_DISAMBIGUATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_delete_disambiguate)
            ],
            DELETE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_delete_confirm)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_delete)],
    )
