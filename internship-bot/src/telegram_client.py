"""Thin Telegram Bot API sender."""
import requests

TIMEOUT = 30


def send(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        print(f"[telegram] network error: {e}")
        return False
    if r.status_code != 200:
        print(f"[telegram] send failed {r.status_code}: {r.text[:300]}")
        return False
    return True


def send_all(token: str, chat_id: str, messages: list) -> bool:
    ok = True
    for msg in messages:
        ok = send(token, chat_id, msg) and ok
    return ok
