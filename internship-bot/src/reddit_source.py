"""Reddit as a supplementary signal.

Reddit hard-blocks anonymous requests from datacenter/CI IPs (GitHub Actions),
so we use Reddit's free OAuth (app-only "client_credentials") when creds are
present, and fall back to the public JSON endpoint otherwise (works locally).
Either way it's isolated and never fatal.
"""
import time
from datetime import datetime, timezone

import requests

UA = {"User-Agent": "python:internship-digest:1.0 (personal opportunity digest)"}
TIMEOUT = 30


def _get_token(settings) -> str:
    if not (settings.reddit_client_id and settings.reddit_client_secret):
        return ""
    try:
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(settings.reddit_client_id, settings.reddit_client_secret),
            headers=UA, timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("access_token", "")
    except (requests.RequestException, ValueError) as e:
        print(f"[reddit] token request failed: {e}")
        return ""


def _relevant(title: str, keywords: list) -> bool:
    low = (title or "").lower()
    return any(k.lower() in low for k in keywords)


def fetch(profile: dict, settings) -> list:
    cfg = profile.get("reddit", {}) or {}
    subs = cfg.get("subreddits", [])
    keywords = cfg.get("keywords", [])
    max_age = cfg.get("max_age_days", 12)
    max_items = cfg.get("max_items", 5)
    if not subs:
        return []

    token = _get_token(settings)
    if token:
        base, headers = "https://oauth.reddit.com", {**UA, "Authorization": f"Bearer {token}"}
    else:
        base, headers = "https://www.reddit.com", UA
        print("[reddit] no OAuth creds — trying anon endpoint (often blocked on CI)")

    query = " OR ".join(keywords) if keywords else "hiring"
    cutoff = datetime.now(timezone.utc).timestamp() - max_age * 86400
    seen_ids, items = set(), []

    for sub in subs:
        suffix = "/search" if token else "/search.json"
        try:
            r = requests.get(
                f"{base}/r/{sub}{suffix}",
                params={"q": query, "restrict_sr": 1, "sort": "new", "t": "month", "limit": 15},
                headers=headers, timeout=TIMEOUT,
            )
            r.raise_for_status()
            children = r.json().get("data", {}).get("children", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[reddit:{sub}] failed: {e}")
            continue

        for child in children:
            d = child.get("data", {})
            pid, title, created = d.get("id"), d.get("title", ""), d.get("created_utc", 0)
            if not pid or pid in seen_ids or created < cutoff:
                continue
            if not _relevant(title, keywords):
                continue
            seen_ids.add(pid)
            items.append({
                "title": title.strip(),
                "org": f"r/{d.get('subreddit', sub)}",
                "location": "", "type": "reddit",
                "link": "https://www.reddit.com" + d.get("permalink", ""),
                "deadline": "", "why_fit": "", "posted": created,
                "source": "reddit", "_created": created,
            })
        time.sleep(1)  # be polite

    items.sort(key=lambda x: x.get("_created", 0), reverse=True)
    print(f"[reddit] {len(items)} recent on-topic posts")
    return items[: max_items * 3]
