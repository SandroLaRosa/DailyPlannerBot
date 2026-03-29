from telegram import Update
from telegram.ext import ContextTypes

from src.classes.event_manager import EventManager
from src.modules.lang_logics import MSG
from src.modules.notify import notify_event


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat and update.message and update.effective_user
    context.bot_data["chat_id"] = update.effective_chat.id
    if context.bot_data["chat_id"] is None:
        return

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


async def help(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat and update.message and update.effective_user
    await update.message.reply_text(
        MSG["help"]["command_list"].format(name=update.effective_user.first_name)
    )


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat and update.message and update.effective_user
    await update.message.reply_text(MSG["restart"]["begin"])
    await start(update, context)
    await update.message.reply_text(MSG["restart"]["end"])


if __name__ == "__main__":
    pass
