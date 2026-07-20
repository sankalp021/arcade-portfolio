"""Orchestrator: gather -> dedupe -> (thrifty Tavily top-up) -> rank -> send -> record.

Run from the project root:  python src/main.py
"""
import sys
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


def gather_free_jobs(settings: Settings, profile: dict) -> list:
    """Free/unmetered sources: Gemini grounding (if quota) + job-board APIs."""
    jobs = []
    jobs += gemini_source.fetch(settings, profile, n=max(settings.max_items + 4, 12))
    jobs += boards.fetch(profile, settings)
    return _dedupe_batch(jobs)


def _merge_new(base_fresh: list, extra: list, seen: dict) -> list:
    """Append genuinely-new, non-duplicate items from `extra` onto base_fresh."""
    have = {j.get("_key") for j in base_fresh}
    for j in dedupe.filter_new(_dedupe_batch(extra), seen):
        if j["_key"] not in have:
            base_fresh.append(j)
            have.add(j["_key"])
    return base_fresh


def main() -> int:
    settings = Settings()
    profile = load_profile()
    name = profile.get("person", {}).get("name", "there")
    keywords = profile.get("keywords", [])

    seen = dedupe.load_seen()

    # 1) Free sources first.
    free_jobs = gather_free_jobs(settings, profile)
    fresh = dedupe.filter_new(free_jobs, seen)
    print(f"[main] {len(free_jobs)} free-source jobs, {len(fresh)} new")

    # 2) Tavily top-up ONLY if the free sources came up short (credit-thrifty).
    tcfg = profile.get("tavily", {}) or {}
    threshold = tcfg.get("only_if_fewer_than", settings.max_items)
    if len(fresh) < threshold:
        print(f"[main] only {len(fresh)} new (< {threshold}) — topping up with Tavily")
        try:
            fresh = _merge_new(fresh, tavily_source.fetch(settings, profile), seen)
        except Exception as e:  # noqa: BLE001 - isolated, never fatal
            print(f"[tavily] fetch error: {e}")
    else:
        print(f"[main] {len(fresh)} new from free sources (>= {threshold}) — skipping Tavily (0 credits)")

    # 3) Reddit (separate section).
    try:
        reddit_posts = dedupe.filter_new(_dedupe_batch(reddit_source.fetch(profile, settings)), seen)
    except Exception as e:  # noqa: BLE001
        print(f"[reddit] fetch error: {e}")
        reddit_posts = []

    net = networking.build(profile)

    fresh.sort(key=lambda j: formatter.score(j, keywords), reverse=True)
    picks = fresh[: settings.max_items]
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
