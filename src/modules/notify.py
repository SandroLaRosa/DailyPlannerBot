from telegram.ext import ContextTypes
from classes.event_manager import EventManager

async def notify_event(context:ContextTypes.DEFAULT_TYPE)->None:
    event_id:str=context.job.data
    em:EventManager=context.job.data["event_manager"]
    chat_id:int=context.bot_data["chat_id"]

    event=em.events.get(event_id)
    if event is None:
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{event.get_message()}",
    )

    em.expire_event(event_id)