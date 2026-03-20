import json
import os
from pathlib import Path

DIR = Path(__file__).parent.parent / "data" / "strings"

def set_lang(lang: str) -> dict:
    path = DIR / f"{lang}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No strings file found for language '{lang}' at {path}"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)

bot_lang = os.getenv("BOT_LANG", "it")
MSG: dict = set_lang(bot_lang)