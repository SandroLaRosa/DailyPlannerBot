import os
from zoneinfo import ZoneInfo

TZ: ZoneInfo = ZoneInfo(os.getenv("BOT_TZ", "Europe/Rome"))
