"""Orchestrator: gather -> dedupe -> rank (top-N per source) -> send -> record.

Run from the project root:  python src/main.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import boards  # noqa: E402
import dedupe  # noqa: E402
import formatter  # noqa: E402
import gemini_source  # noqa: E402
import networking  # noqa: E402
import reddit_source  # noqa: E402
import tavily_source  # noqa: E402
import telegram_client  # noqa: E402
from config import Settings, load_profile  # noqa: E402


def _dedupe_batch(items: list) -> list:
    unique, keys = [], set()
    for it in items:
        k = dedupe.job_key(it)
        if k in keys:
            continue
        keys.add(k)
        unique.append(it)
    return unique


def _base_source(job: dict) -> str:
    return (job.get("source", "") or "").split(":")[0]


def gather_jobs(settings: Settings, profile: dict) -> list:
    """All job sources: Gemini grounding (if quota) + boards + Tavily web search."""
    jobs = []
    jobs += gemini_source.fetch(settings, profile, n=max(settings.max_items + 4, 12))
    jobs += boards.fetch(profile, settings)
    try:
        jobs += tavily_source.fetch(settings, profile)
    except Exception as e:  # noqa: BLE001 - isolated, never fatal
        print(f"[tavily] fetch error: {e}")
    return _dedupe_batch(jobs)


def select_jobs(fresh: list, keywords: list, per_min: int, per_max: int, cap: int) -> list:
    """Balanced selection: guarantee each source's top `per_min` (by fit), then
    fill up to `cap` with the best remaining — but never more than `per_max` from
    any single source, so no one source floods the digest."""
    fit = lambda j: formatter.score(j, keywords)  # noqa: E731
    ranked = sorted(fresh, key=fit, reverse=True)

    by_src = defaultdict(list)
    for j in ranked:
        by_src[_base_source(j)].append(j)

    picks, used, count = [], set(), defaultdict(int)
    for src, items in by_src.items():
        for j in items[:per_min]:
            picks.append(j)
            used.add(j["_key"])
            count[src] += 1
    for j in ranked:
        if len(picks) >= cap:
            break
        src, k = _base_source(j), j["_key"]
        if k in used or count[src] >= per_max:
            continue
        picks.append(j)
        used.add(k)
        count[src] += 1

    picks.sort(key=fit, reverse=True)
    return picks


def main() -> int:
    settings = Settings()
    profile = load_profile()
    name = profile.get("person", {}).get("name", "there")
    keywords = profile.get("keywords", [])
    dcfg = profile.get("digest", {}) or {}
    per_min = dcfg.get("per_source_min", 3)
    per_max = dcfg.get("per_source_max", 6)
    cap = dcfg.get("max_items", settings.max_items)

    seen = dedupe.load_seen()

    all_jobs = gather_jobs(settings, profile)
    fresh = dedupe.filter_new(all_jobs, seen)
    print(f"[main] {len(all_jobs)} jobs gathered, {len(fresh)} new")

    # Reddit section (Tavily-powered search + any OAuth results), separate list.
    reddit_raw = []
    try:
        reddit_raw += reddit_source.fetch(profile, settings)
    except Exception as e:  # noqa: BLE001
        print(f"[reddit] fetch error: {e}")
    try:
        reddit_raw += tavily_source.fetch_reddit(settings, profile)
    except Exception as e:  # noqa: BLE001
        print(f"[tavily-reddit] fetch error: {e}")
    reddit_posts = dedupe.filter_new(_dedupe_batch(reddit_raw), seen)

    net = networking.build(profile)

    picks = select_jobs(fresh, keywords, per_min, per_max, cap)
    reddit_picks = reddit_posts[: profile.get("reddit", {}).get("max_items", 5)]
    print(f"[main] {len(picks)} jobs + {len(reddit_picks)} reddit posts to send")

    if not picks and not reddit_picks:
        print("[main] nothing new to send today")
        if settings.send_when_empty and not settings.dry_run:
            telegram_client.send(
                settings.telegram_token, settings.telegram_chat_id,
                f"👋 {name}, no new matching openings surfaced today. Looking again tomorrow.",
            )
        return 0

    messages = formatter.build_messages(picks, name, reddit_posts=reddit_picks, networking=net)

    if settings.dry_run:
        print("\n===== DRY RUN (not sending) =====")
        for m in messages:
            print(m)
            print("-----")
        return 0

    if not settings.telegram_token or not settings.telegram_chat_id:
        print("[main] missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID — cannot send")
        return 1

    ok = telegram_client.send_all(settings.telegram_token, settings.telegram_chat_id, messages)
    if ok:
        dedupe.commit_seen(picks + reddit_picks, seen)
        print(f"[main] sent {len(picks)} jobs + {len(reddit_picks)} reddit posts; updated seen state")
        return 0
    print("[main] send failed — NOT recording as seen so they retry next run")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
