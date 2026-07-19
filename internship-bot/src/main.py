"""Orchestrator: gather -> dedupe -> rank -> send -> record.

Run from the project root:  python src/main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import boards  # noqa: E402
import dedupe  # noqa: E402
import formatter  # noqa: E402
import gemini_source  # noqa: E402
import telegram_client  # noqa: E402
from config import Settings, load_profile  # noqa: E402


def gather(settings: Settings, profile: dict) -> list:
    jobs = []
    jobs += gemini_source.fetch(settings, profile, n=max(settings.max_items + 4, 12))
    jobs += boards.fetch(profile)

    # de-duplicate within this run (grounding + boards can overlap)
    unique, seen_keys = [], set()
    for j in jobs:
        k = dedupe.job_key(j)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        unique.append(j)
    return unique


def main() -> int:
    settings = Settings()
    profile = load_profile()
    name = profile.get("person", {}).get("name", "there")
    keywords = profile.get("keywords", [])

    all_jobs = gather(settings, profile)
    print(f"[main] {len(all_jobs)} unique openings gathered")

    seen = dedupe.load_seen()
    fresh = dedupe.filter_new(all_jobs, seen)
    print(f"[main] {len(fresh)} are new since last run")

    fresh.sort(key=lambda j: formatter.score(j, keywords), reverse=True)
    picks = fresh[: settings.max_items]

    if not picks:
        print("[main] nothing new to send today")
        if settings.send_when_empty and not settings.dry_run:
            telegram_client.send(
                settings.telegram_token,
                settings.telegram_chat_id,
                f"👋 {name}, no new matching openings surfaced today. "
                "I'll keep looking tomorrow.",
            )
        return 0

    messages = formatter.build_messages(picks, name)

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
        dedupe.commit_seen(picks, seen)
        print(f"[main] sent {len(picks)} openings and updated seen state")
        return 0
    print("[main] send failed — NOT recording as seen so they retry next run")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
