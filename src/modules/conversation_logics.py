from __future__ import annotations

from datetime import datetime

import re

from dateutil import parser as dtparser
from dateutil.relativedelta import relativedelta

from modules.timezone_logics import TZ
from modules.lang_logics import MSG


from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from classes.event import Event, RecurringEvent, Reminder
from classes.event_manager import EventManager
from modules.notify import notify_event

# States
(NAME, EVENT_TYPE, START_DATE, END_DATE, HAS_DESCRIPTION, DESCRIPTION, FREQ, PERIOD, CUSTOM_PERIOD, CONFIRM,) = range(10)

# Custom Keyboards
YES_NO = ReplyKeyboardMarkup(
    [["Sì", "No"]], one_time_keyboard=True, resize_keyboard=True,
)

EVENT_TYPE = ReplyKeyboardMarkup(
    [["Evento", "Evento ricorrente", "Promemoria"]], one_time_keyboard=True, resize_keyboard=True,
)

PERIOD = ReplyKeyboardMarkup(
    [["giornaliero", "settimanale"], ["mensile", "annuale"], ["custom"]], one_time_keyboard=True, resize_keyboard=True,
)

CONFIRM = ReplyKeyboardMarkup(
    [["Conferma", "Annulla"]], one_time_keyboard=True, resize_keyboard=True,
)

# Time Mapper
PERIOD_MAP: dict[str, relativedelta] = {
    "giornaliero": relativedelta(days=1),
    "settimanale": relativedelta(weeks=1),
    "mensile":     relativedelta(months=1),
    "annuale":     relativedelta(years=1),
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
    "anno": "years",   "anni": "years",
    "mese": "months",  "mesi": "months",
    "settimana": "weeks", "settimane": "weeks",
    "giorno": "days",  "giorni": "days",
    "ora": "hours",    "ore": "hours",
    "minuto": "minutes", "minuti": "minutes",
    "secondo": "seconds", "secondi": "seconds",
}

DURATION_RE = re.compile(
    r"(\d+)\s+(" + "|".join(UNIT_MAP.keys()) + r")",
    re.IGNORECASE,
)

def _parse_duration(text: str) -> relativedelta | None:
    kwargs: dict[str, int] = {}
    for match in DURATION_RE.finditer(text):
        amount = int(match.group(1))
        unit   = UNIT_MAP[match.group(2).lower()]
        kwargs[unit] = kwargs.get(unit, 0) + amount
    return relativedelta(**kwargs) if kwargs else None


def _is_yes(text: str) -> bool:
    return text in {"sì", "si", "yes", "yep"}


def _is_no(text: str) -> bool:
    return text in {"no", "nope"}


def _format_period(rd: relativedelta) -> str:
    parts: list[str] = []
    if rd.years:   parts.append(f"{rd.years} ann{'o' if rd.years == 1 else 'i'}")
    if rd.months:  parts.append(f"{rd.months} mes{'e' if rd.months == 1 else 'i'}")
    if rd.days:    parts.append(f"{rd.days} giorn{'o' if rd.days == 1 else 'i'}")
    if rd.hours:   parts.append(f"{rd.hours} or{'a' if rd.hours == 1 else 'e'}")
    if rd.minutes: parts.append(f"{rd.minutes} minut{'o' if rd.minutes == 1 else 'i'}")
    return ", ".join(parts) if parts else "—"


# Start
async def start_event_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        f"Ok {update.effective_user.first_name}, creiamo un nuovo evento.\n"
        "Come si chiama l'evento?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "Che tipo di evento vuoi creare?",
        reply_markup=EVENT_TYPE,
    )
    return EVENT_TYPE

async def get_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip().lower()

    if choice == "evento":
        context.user_data["event_type"] = "single"
    elif choice == "evento ricorrente":
        context.user_data["event_type"] = "recurring"
    elif choice == "promemoria":
        context.user_data["event_type"] = "reminder"
    else:
        await update.message.reply_text(
            "Scegli una delle opzioni disponibili.",
            reply_markup=EVENT_TYPE,
        )
        return EVENT_TYPE

    await update.message.reply_text(
        "Quando inizia?\n(es. 25/06/2025 15:00  oppure  25 giugno 2025 15:00)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return START_DATE

async def get_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dt = _parse_future_dt(update.message.text)
    if dt is None:
        await update.message.reply_text(
            "Non ho capito la data, riprova.\n"
            "Controlla che sia una data futura!!!\n"
            "Usa il formato: 25/06/2025 15:00  oppure  25 giugno 2025 15:00"
        )
        return START_DATE

    context.user_data["start_date"] = dt

    # Reminder has no end date and needs a description
    if context.user_data["event_type"] == "reminder":
        await update.message.reply_text(
            "Inserisci una descrizione per il promemoria:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return DESCRIPTION

    await update.message.reply_text("Ok, e quando finisce?")
    return END_DATE

async def get_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    start: datetime = context.user_data["start_date"]
    dt = _parse_future_dt(update.message.text)

    if dt is None:
        await update.message.reply_text(
            "Non ho capito la data, riprova.\n"
            "Usa il formato: 25/06/2025 18:00  oppure  25 giugno 2025 18:00"
        )        
        return END_DATE

    if dt <= start:
        await update.message.reply_text(
            "Un evento non può finire prima di cominciare, riprova."
        )
        return END_DATE

    context.user_data["end_date"] = dt
    await update.message.reply_text(
        "Vuoi aggiungere una descrizione?",
        reply_markup=YES_NO,
    )
    return HAS_DESCRIPTION

async def get_has_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text.strip().lower()

    if _is_no(answer):
        context.user_data["description"] = None
        return await _after_description(update, context)

    if _is_yes(answer):
        await update.message.reply_text(
            "Inserisci una descrizione:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return DESCRIPTION

    await update.message.reply_text("Rispondi con 'Sì' o 'No'.", reply_markup=YES_NO)
    return HAS_DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["description"] = update.message.text.strip()
    return await _after_description(update, context)

async def _after_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if context.user_data["event_type"] == "recurring":
        await update.message.reply_text(
            "Quante volte si ripete l'evento? (inserisci un numero in cifre)",
            reply_markup=ReplyKeyboardRemove(),
        )
        return FREQ
    return await show_recap(update, context)

async def get_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        freq = int(update.message.text.strip())
        if freq <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Inserisci un numero intero positivo.")
        return FREQ

    context.user_data["freq"] = freq
    await update.message.reply_text(
        "Con che intervallo dovrei riproporre l'evento?",
        reply_markup=PERIOD,
    )
    return PERIOD

async def get_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    period_str = update.message.text.strip().lower()
    valid = set(PERIOD_MAP.keys()) | {"custom"}

    if period_str not in valid:
        await update.message.reply_text(
            "Scegli una delle opzioni disponibili.", reply_markup=PERIOD
        )
        return PERIOD

    if period_str == "custom":
        await update.message.reply_text(
            "Inserisci il periodo personalizzato\n"
            "(es. 10 giorni  ·  2 settimane  ·  1 mese e 3 giorni  ·  4 ore e 30 minuti):",
            reply_markup=ReplyKeyboardRemove(),
        )
        return CUSTOM_PERIOD

    context.user_data["period"] = PERIOD_MAP[period_str]
    return await show_recap(update, context)

async def get_custom_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    delta = _parse_duration(update.message.text.strip())
    if delta is None:
        await update.message.reply_text(
            "Non ho capito la durata, riprova.\n"
            "Inserisci quantità e unità, es: 3 giorni  ·  2 settimane  ·  1 mese e 4 ore"
        )
        return CUSTOM_PERIOD

    context.user_data["period"] = delta
    return await show_recap(update, context)

async def show_recap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = context.user_data
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
        "\n".join(lines), parse_mode="Markdown", reply_markup=CONFIRM
    )
    return CONFIRM


async def get_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    risposta = update.message.text.strip().lower()

    if "annulla" in risposta:
        await update.message.reply_text(
            "Creazione annullata.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if "conferma" not in risposta:
        await update.message.reply_text(
            "Scegli Conferma o Annulla.", reply_markup=CONFIRM
        )
        return CONFIRM

    d = context.user_data
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Operazione annullata.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def add_event_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("crea_evento", start_event_creation)],
        states={
            NAME:            [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EVENT_TYPE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_type)],
            START_DATE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_date)],
            END_DATE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_date)],
            HAS_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_has_description)],
            DESCRIPTION:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            FREQ:            [MessageHandler(filters.TEXT & ~filters.COMMAND, get_frequency)],
            PERIOD:          [MessageHandler(filters.TEXT & ~filters.COMMAND, get_period)],
            CUSTOM_PERIOD:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_period)],
            CONFIRM:         [MessageHandler(filters.TEXT & ~filters.COMMAND, get_confirm)],
        },
        fallbacks=[CommandHandler("annulla", cancel)],
    )