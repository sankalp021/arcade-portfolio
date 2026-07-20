"""Reddit as a supplementary signal, via the public JSON API (no key needed).

Searches a handful of relevant subreddits for recent, on-topic posts (hiring
threads, internship calls, etc.). Noisier than job boards, so we filter hard on
keywords + recency and keep it a small section.
"""
import time
from datetime import datetime, timezone

import requests

UA = {"User-Agent": "internship-bot/1.0 (personal opportunity digest)"}
TIMEOUT = 30


def _relevant(title: str, keywords: list) -> bool:
    low = (title or "").lower()
    return any(k.lower() in low for k in keywords)


def fetch(profile: dict) -> list:
    cfg = profile.get("reddit", {}) or {}
    subs = cfg.get("subreddits", [])
    keywords = cfg.get("keywords", [])
    max_age = cfg.get("max_age_days", 12)
    max_items = cfg.get("max_items", 5)
    if not subs:
        return []

    query = " OR ".join(keywords) if keywords else "hiring"
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - max_age * 86400
    seen_ids, items = set(), []

    for sub in subs:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/search.json",
                params={"q": query, "restrict_sr": 1, "sort": "new", "t": "month", "limit": 15},
                headers=UA, timeout=TIMEOUT,
            )
            r.raise_for_status()
            children = r.json().get("data", {}).get("children", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[reddit:{sub}] failed: {e}")
            continue

        for child in children:
            d = child.get("data", {})
            pid = d.get("id")
            title = d.get("title", "")
            created = d.get("created_utc", 0)
            if not pid or pid in seen_ids:
                continue
            if created < cutoff:
                continue
            if not _relevant(title, keywords):
                continue
            seen_ids.add(pid)
            items.append({
                "title": title.strip(),
                "org": f"r/{d.get('subreddit', sub)}",
                "location": "",
                "type": "reddit",
                "link": "https://www.reddit.com" + d.get("permalink", ""),
                "deadline": "",
                "why_fit": "",
                "source": "reddit",
                "_created": created,
            })
        time.sleep(1)  # be polite to Reddit's unauthenticated endpoint

    items.sort(key=lambda x: x.get("_created", 0), reverse=True)
    print(f"[reddit] {len(items)} recent on-topic posts")
    return items[: max_items * 3]  # over-fetch; dedupe/cap happens downstream
