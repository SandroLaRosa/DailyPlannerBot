from telegram import Update
from telegram.ext import ContextTypes

from classes.event_manager import EventManager
from modules.notify import notify_event
from modules.lang_logics import MSG

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    em: EventManager = context.bot_data["event_manager"]
    valid, missed = em.load_ongoing()

    await update.message.reply_text(
        MSG["start"]["greeting"].format(name=update.effective_user.first_name)
    )

    for ev in valid:
        em.schedule(ev, context.application, notify_event)

    if missed:
        lines = [MSG["start"]["checking_missed"]]
        for ev in missed:
            lines.append(MSG["start"]["missed_item"].format(message=ev.get_message()))
        await update.message.reply_text("\n".join(lines))
    else:
        await update.message.reply_text(MSG["start"]["no_missed"])

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE)->None:
    await update.message.reply_text(
        MSG["help"]["command_list"].format(name=update.effective_user.first_name)
    )

if __name__ == "__main__":
    pass