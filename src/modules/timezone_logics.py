import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.getenv("BOT_TZ", "Europe/Rome"))