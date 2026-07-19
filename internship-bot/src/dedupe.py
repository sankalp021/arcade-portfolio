"""Persistent 'already sent' state so Ipshita never gets the same job twice.

State lives in state/seen.json (a map of job-key -> first-seen date) and is
committed back to the repo by the GitHub Action after each run.
"""
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state" / "seen.json"
RETENTION_DAYS = 45  # drop entries older than this so the file stays small


def job_key(job: dict) -> str:
    """Stable id for a listing, based on org+title (falls back to link)."""
    basis = f"{job.get('org', '')}|{job.get('title', '')}".lower()
    basis = re.sub(r"[^a-z0-9]+", "", basis)
    if not basis:
        basis = (job.get("link", "") or "").lower()
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def load_seen() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def filter_new(jobs: list, seen: dict) -> list:
    """Return only jobs we haven't sent before; tags each with its key."""
    fresh = []
    for j in jobs:
        k = job_key(j)
        if k in seen:
            continue
        j["_key"] = k
        fresh.append(j)
    return fresh


def _parse(d: str) -> date:
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return date.today()


def commit_seen(sent_jobs: list, seen: dict) -> None:
    """Record today's sent jobs, prune old entries, write back to disk."""
    today = date.today().isoformat()
    for j in sent_jobs:
        seen[j.get("_key") or job_key(j)] = today

    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    seen = {k: v for k, v in seen.items() if _parse(v) >= cutoff}

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(seen, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
