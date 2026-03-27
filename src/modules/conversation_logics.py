from __future__ import annotations

import re
from datetime import datetime

from dateutil import parser as dtparser
from dateutil.relativedelta import relativedelta
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (CommandHandler, ContextTypes, ConversationHandler,
                          MessageHandler, filters)

from src.classes.event import Event, RecurringEvent, Reminder
from src.classes.event_manager import EventManager
from src.modules.notify import notify_event
from src.modules.timezone_logics import TZ

# States
(
    NAME,
    EVENT_TYPE,
    START_DATE,
    END_DATE,
    HAS_DESCRIPTION,
    DESCRIPTION,
    FREQ,
    PERIOD,
    CUSTOM_PERIOD,
    CONFIRM,
) = range(10)

# Custom Keyboards
YES_NO_KEY = ReplyKeyboardMarkup(
    [["Sì", "No"]],
    one_time_keyboard=True,
    resize_keyboard=True,
)

EVENT_TYPE_KEY = ReplyKeyboardMarkup(
    [["Evento", "Evento ricorrente", "Promemoria"]],
    one_time_keyboard=True,
    resize_keyboard=True,
)

PERIOD_KEY = ReplyKeyboardMarkup(
    [["giornaliero", "settimanale"], ["mensile", "annuale"], ["custom"]],
    one_time_keyboard=True,
    resize_keyboard=True,
)

CONFIRM_KEY = ReplyKeyboardMarkup(
    [["Conferma", "Annulla"]],
    one_time_keyboard=True,
    resize_keyboard=True,
)

# Time Mapper
PERIOD_MAP: dict[str, relativedelta] = {
    "giornaliero": relativedelta(days=1),
    "settimanale": relativedelta(weeks=1),
    "mensile": relativedelta(months=1),
    "annuale": relativedelta(years=1),
}


# Helpers
def _parse_future_dt(text: str) -> datetime | None:
    try:
        dt = dtparser.parse(text, dayfirst=True, fuzzy=True)
    except (dtparser.ParserError, OverflowError, ValueError):
        return None
    dt = dt.replace(tzinfo=TZ)
    return dt if dt > datetime.now(TZ) else None


UNIT_MAP: dict[str, str] = {
    "anno": "years",
    "anni": "years",
    "mese": "months",
    "mesi": "months",
    "settimana": "weeks",
    "settimane": "weeks",
    "giorno": "days",
    "giorni": "days",
    "ora": "hours",
    "ore": "hours",
    "minuto": "minutes",
    "minuti": "minutes",
    "secondo": "seconds",
    "secondi": "seconds",
}

DURATION_RE = re.compile(
    r"(\d+)\s+(" + "|".join(UNIT_MAP.keys()) + r")",
    re.IGNORECASE,
)


def _parse_duration(text: str) -> relativedelta | None:
    years = months = weeks = days = hours = minutes = seconds = 0
    found = False
    for match in DURATION_RE.finditer(text):
        amount = int(match.group(1))
        unit = UNIT_MAP[match.group(2).lower()]
        found = True
        if unit == "years":
            years += amount
        elif unit == "months":
            months += amount
        elif unit == "weeks":
            weeks += amount
        elif unit == "days":
            days += amount
        elif unit == "hours":
            hours += amount
        elif unit == "minutes":
            minutes += amount
        elif unit == "seconds":
            seconds += amount
    if not found:
        return None
    return relativedelta(
        years=years,
        months=months,
        weeks=weeks,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )


def _is_yes(text: str) -> bool:
    return text in {"sì", "si", "yes", "yep"}


def _is_no(text: str) -> bool:
    return text in {"no", "nope"}


def _format_period(rd: relativedelta) -> str:
    parts: list[str] = []
    if rd.years:
        parts.append(f"{rd.years} ann{'o' if rd.years == 1 else 'i'}")
    if rd.months:
        parts.append(f"{rd.months} mes{'e' if rd.months == 1 else 'i'}")
    if rd.days:
        parts.append(f"{rd.days} giorn{'o' if rd.days == 1 else 'i'}")
    if rd.hours:
        parts.append(f"{rd.hours} or{'a' if rd.hours == 1 else 'e'}")
    if rd.minutes:
        parts.append(f"{rd.minutes} minut{'o' if rd.minutes == 1 else 'i'}")
    return ", ".join(parts) if parts else "—"


def _user_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Return user_data, asserting it is not None."""
    assert context.user_data is not None
    return context.user_data


def _text(update: Update) -> str:
    """Return message text, asserting both message and text are not None."""
    assert update.message is not None and update.message.text is not None
    return update.message.text


# Start
async def start_event_creation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    assert update.effective_chat and update.message and update.effective_user
    _user_data(context).clear()
    await update.message.reply_text(
        f"Ok {update.effective_user.first_name}, creiamo un nuovo evento.\n"
        "Come si chiama l'evento?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    _user_data(context)["name"] = _text(update).strip()
    await update.message.reply_text(
        "Che tipo di evento vuoi creare?",
        reply_markup=EVENT_TYPE_KEY,
    )
    return EVENT_TYPE


async def get_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    choice = _text(update).strip().lower()

    if choice == "evento":
        _user_data(context)["event_type"] = "single"
    elif choice == "evento ricorrente":
        _user_data(context)["event_type"] = "recurring"
    elif choice == "promemoria":
        _user_data(context)["event_type"] = "reminder"
    else:
        await update.message.reply_text(
            "Scegli una delle opzioni disponibili.",
            reply_markup=EVENT_TYPE_KEY,
        )
        return EVENT_TYPE

    await update.message.reply_text(
        "Quando inizia?\n(es. 25/06/2025 15:00)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return START_DATE


async def get_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    dt = _parse_future_dt(_text(update))
    if dt is None:
        await update.message.reply_text(
            "Non ho capito la data, riprova.\n"
            "Controlla che sia una data futura!!!\n"
            "Usa il formato: 25/06/2026 15:00"
        )
        return START_DATE

    _user_data(context)["start_date"] = dt

    # Reminder has no end date and needs a description
    if _user_data(context)["event_type"] == "reminder":
        await update.message.reply_text(
            "Inserisci una descrizione per il promemoria:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return DESCRIPTION

    await update.message.reply_text("Ok, e quando finisce?")
    return END_DATE


async def get_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    start: datetime = _user_data(context)["start_date"]
    dt = _parse_future_dt(_text(update))

    if dt is None:
        await update.message.reply_text(
            "Non ho capito la data, riprova.\nUsa il formato: 25/06/2025 18:00"
        )
        return END_DATE

    if dt <= start:
        await update.message.reply_text(
            "Un evento non può finire prima di cominciare, riprova."
        )
        return END_DATE

    _user_data(context)["end_date"] = dt
    await update.message.reply_text(
        "Vuoi aggiungere una descrizione?",
        reply_markup=YES_NO_KEY,
    )
    return HAS_DESCRIPTION


async def get_has_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    assert update.effective_chat and update.message and update.effective_user
    answer = _text(update).strip().lower()

    if _is_no(answer):
        _user_data(context)["description"] = None
        return await _after_description(update, context)

    if _is_yes(answer):
        await update.message.reply_text(
            "Inserisci una descrizione:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return DESCRIPTION

    await update.message.reply_text(
        "Rispondi con 'Sì' o 'No'.", reply_markup=YES_NO_KEY
    )
    return HAS_DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    _user_data(context)["description"] = _text(update).strip()
    return await _after_description(update, context)


async def _after_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    if _user_data(context)["event_type"] == "recurring":
        await update.message.reply_text(
            "Quante volte si ripete l'evento? (inserisci un numero in cifre)",
            reply_markup=ReplyKeyboardRemove(),
        )
        return FREQ
    return await show_recap(update, context)


async def get_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    try:
        freq = int(_text(update).strip())
        if freq <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Inserisci un numero intero positivo.")
        return FREQ

    _user_data(context)["freq"] = freq
    await update.message.reply_text(
        "Con che intervallo dovrei riproporre l'evento?",
        reply_markup=PERIOD_KEY,
    )
    return PERIOD


async def get_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    period_str = _text(update).strip().lower()
    valid = set(PERIOD_MAP.keys()) | {"custom"}

    if period_str not in valid:
        await update.message.reply_text(
            "Scegli una delle opzioni disponibili.", reply_markup=PERIOD_KEY
        )
        return PERIOD

    if period_str == "custom":
        await update.message.reply_text(
            "Inserisci il periodo personalizzato\n"
            "(es. 10 giorni, 2 settimane, 1 mese, 4 ore o 30 minuti):",
            reply_markup=ReplyKeyboardRemove(),
        )
        return CUSTOM_PERIOD

    _user_data(context)["period"] = PERIOD_MAP[period_str]
    return await show_recap(update, context)


async def get_custom_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    delta = _parse_duration(_text(update).strip())
    if delta is None:
        await update.message.reply_text(
            "Non ho capito la durata, riprova.\n"
            "Inserisci quantità e unità, es: 3 giorni, 2 settimane,  1 mese o 4 ore"
        )
        return CUSTOM_PERIOD

    _user_data(context)["period"] = delta
    return await show_recap(update, context)


async def show_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    d = _user_data(context)
    event_type: str = d["event_type"]
    start_str = d["start_date"].strftime("%d/%m/%Y %H:%M")

    lines = ["Riepilogo\n", f"Nome: {d['name']}"]

    if event_type == "reminder":
        lines.append(f"Data: {start_str}")
        lines.append(f"Descrizione: {d.get('description') or '—'}")
    else:
        end_str = d["end_date"].strftime("%d/%m/%Y %H:%M")
        lines.append(f"Inizio: {start_str}")
        lines.append(f"Fine: {end_str}")
        lines.append(f"Descrizione: {d.get('description') or '—'}")
        if event_type == "recurring":
            lines.append(f"Ripetizioni: {d['freq']} volte")
            lines.append(f"Periodo: {_format_period(d['period'])}")

    lines.append("\nConfermi?")
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=CONFIRM_KEY
    )
    return CONFIRM


async def get_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_chat and update.message and update.effective_user
    risposta = _text(update).strip().lower()

    if "annulla" in risposta:
        await update.message.reply_text(
            "Creazione annullata.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if "conferma" not in risposta:
        await update.message.reply_text(
            "Scegli Conferma o Annulla.", reply_markup=CONFIRM_KEY
        )
        return CONFIRM

    d = _user_data(context)
    event_type: str = d["event_type"]

    if event_type == "reminder":
        new_event: Event = Reminder(
            name=d["name"],
            start_date=d["start_date"],
            description=d["description"],
        )
    elif event_type == "recurring":
        new_event = RecurringEvent(
            name=d["name"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            period=d["period"],
            remaining_occurrences=d["freq"],
            description=d.get("description"),
        )
    else:
        new_event = Event(
            name=d["name"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            description=d.get("description"),
        )

    em: EventManager = context.bot_data["event_manager"]
    em.add_event(new_event, context.application, notify_event)

    await update.message.reply_text(
        f"Evento '{new_event.name}' creato!",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.message
    await update.message.reply_text(
        "Operazione annullata.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def add_event_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("crea_evento", start_event_creation)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EVENT_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_type)
            ],
            START_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_date)
            ],
            END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_date)],
            HAS_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_has_description)
            ],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)
            ],
            FREQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_frequency)],
            PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_period)],
            CUSTOM_PERIOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_period)
            ],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_confirm)],
        },
        fallbacks=[CommandHandler("annulla", cancel)],
    )
