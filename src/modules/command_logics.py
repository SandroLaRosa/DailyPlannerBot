from telegram import Update
from telegram.ext import ContextTypes

from classes.event import Event
from classes.event_manager import EventManager

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE)->None:
    em: EventManager = context.bot_data["event_manager"]
    valid, missed = em.load_ongoing()

    await update.message.reply_text(
        f"Ciao {update.effective_user.first_name}\n"
        "Grazie per aver scelto \"DailyPlannerBot\" per la gestione della tua agenda\n"
        "Fammi controllare se dall'ultima sessione hai perso qualche evento."
    )
    for ev in valid:
        em.schedule(ev, context.application, notify_event) #TODO scrivere notify event
    if missed:
        lines = ["Mentre il server era offline hai perso questi eventi:\n"]
        for ev in missed:
            lines.append(f"*\t{ev.get_message()}")
        await update.message.reply_text("\n".join(lines))
    else:
        await update.message.reply_text("Perfetto nessun messaggio perso dall'ultima sessione")
    
    


if __name__ =="__main__":
    pass