from telegram.ext import ContextTypes

from src.classes.event_manager import EventManager


async def notify_event(context: ContextTypes.DEFAULT_TYPE) -> None:
    assert context.job is not None
    assert isinstance(context.job.data, str)
    event_id: str = context.job.data
    em: EventManager = context.bot_data["event_manager"]
    chat_id: int = context.bot_data["chat_id"]

    event = em.events.get(event_id)
    if event is None:
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{event.get_message()}",
    )

    em.expire_event(event_id, app=context.application, callback=notify_event)
