"""Loads settings from environment + the profile YAML."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on")


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip()
        self.telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        # Adzuna is optional — gives real India coverage. Free keys: developer.adzuna.com
        self.adzuna_app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
        self.adzuna_app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
        # Reddit OAuth (optional but recommended — Reddit blocks anon requests from
        # CI IPs). Free "script" app at reddit.com/prefs/apps.
        self.reddit_client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
        self.reddit_client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
        # Tavily: LLM-grade web search (real current listings + links). Free tier.
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY", "").strip()
        self.max_items = int(os.environ.get("MAX_ITEMS", "10") or "10")
        self.dry_run = _flag("DRY_RUN", False)
        self.send_when_empty = _flag("SEND_WHEN_EMPTY", False)


def load_profile() -> dict:
    with open(ROOT / "config" / "profile.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)
