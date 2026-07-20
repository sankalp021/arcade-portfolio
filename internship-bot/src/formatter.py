"""Builds the Telegram digest: jobs grouped into meaningful sections, with
posting dates and a source tag per item, plus Reddit and LinkedIn sections."""
import html
from datetime import date, datetime, timezone


def _esc(s: str) -> str:
    return html.escape(str(s or ""), quote=False)


def score(job: dict, keywords: list) -> int:
    """Relevance score: profile-keyword hits, nudged toward her core domains,
    internships, and India (her winter-internship + placement goal)."""
    blob = " ".join([job.get("title", ""), job.get("org", ""), job.get("why_fit", "")]).lower()
    s = sum(1 for k in keywords if k.lower() in blob)
    for boost in ("esg", "sustainab", "climate", "carbon", "ghg", "finance", "investment"):
        if boost in blob:
            s += 1
    if "intern" in blob:
        s += 2
    if _is_india(job):
        s += 2
    return s


# ---- classification -------------------------------------------------------

INDIA_HINTS = (
    "india", "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad", "pune",
    "chennai", "kolkata", "gurgaon", "gurugram", "noida", "bhopal", "ahmedabad",
    "jaipur", "remote india",
)


def _is_india(job: dict) -> bool:
    if job.get("source") in ("unstop", "adzuna"):
        return True
    blob = " ".join([job.get("location", ""), job.get("title", ""), job.get("why_fit", "")]).lower()
    return any(h in blob for h in INDIA_HINTS)


def _is_intern(job: dict) -> bool:
    return "intern" in (job.get("title", "") + " " + job.get("type", "")).lower()


def _bucket(job: dict) -> str:
    if _is_india(job):
        return "intern_in" if _is_intern(job) else "job_in"
    return "remote"


BUCKETS = [
    ("intern_in", "🎓 Internships · India"),
    ("job_in", "💼 Jobs / Placements · India"),
    ("remote", "🌍 Remote / Global"),
]

SOURCE_LABELS = {
    "unstop": "Unstop", "adzuna": "Adzuna", "jobicy": "Jobicy",
    "remotive": "Remotive", "themuse": "The Muse", "tavily": "Web search",
    "greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby", "workday": "Workday",
}


def _source_label(source: str) -> str:
    base = (source or "").split(":")[0]
    return SOURCE_LABELS.get(base, base.title())


def _posted(raw) -> str:
    """Human 'posted' string from an ISO date, epoch (s or ms), or a Workday-style
    'Posted 3 Days Ago' phrase. Returns '' if unknown."""
    if raw in (None, "", 0):
        return ""
    if isinstance(raw, str):
        low = raw.lower()
        if "ago" in low or "posted" in low:  # already human (Workday)
            return raw.replace("Posted", "").replace("posted", "").strip().rstrip(".")
    dt = None
    try:
        if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.isdigit()):
            ts = float(raw)
            if ts > 1e12:  # milliseconds
                ts /= 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, OverflowError, OSError):
        try:
            dt = datetime.strptime(str(raw)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - dt).days
    if days <= 0:
        return "today"
    if days == 1:
        return "1d ago"
    if days < 30:
        return f"{days}d ago"
    return dt.strftime("%d %b")


# ---- rendering ------------------------------------------------------------

def _format_job(idx: int, job: dict) -> str:
    title = _esc(job.get("title", "Role"))
    org = _esc(job.get("org", ""))
    head = f"<b>{idx}. {title}</b>" + (f" — {org}" if org else "")

    meta = []
    if job.get("location"):
        meta.append(f"📍 {_esc(job['location'])}")
    posted = _posted(job.get("posted", ""))
    if posted:
        meta.append(f"🗓 {_esc(posted)}")
    if job.get("type"):
        meta.append(f"🏷 {_esc(job['type'])}")
    src = _source_label(job.get("source", ""))
    if src:
        meta.append(f"via {_esc(src)}")

    lines = [head]
    if meta:
        lines.append(" · ".join(meta))
    if job.get("deadline"):
        lines.append(f"⏳ Deadline: {_esc(job['deadline'])}")
    if job.get("why_fit"):
        lines.append(f"<i>{_esc(job['why_fit'])}</i>")
    lines.append(f'<a href="{_esc(job.get("link", ""))}">Open listing →</a>')
    return "\n".join(lines)


def _reddit_block(posts: list) -> list:
    blocks = ["👾 <b>From Reddit</b> <i>(recent, unverified — skim these)</i>"]
    for p in posts:
        blocks.append(
            f'• <a href="{_esc(p.get("link", ""))}">{_esc(p.get("title", "(post)"))}</a>'
            f' <i>{_esc(p.get("org", ""))}</i>'
        )
    return blocks


def _networking_block(networking: dict) -> str:
    lines = ["🌐 <b>Networking — LinkedIn</b> <i>(open &amp; send connection requests)</i>"]
    for item in networking.get("links", []):
        tag = "🧑‍💼" if item.get("kind") == "people" else "💼"
        lines.append(f'{tag} <a href="{_esc(item.get("url", ""))}">{_esc(item.get("label", ""))}</a>')
    templates = networking.get("note_templates", [])
    if templates:
        lines.append("<i>Connection-note templates:</i>")
        for label, text in templates:
            lines.append(f"<i>· {_esc(label)}:</i> {_esc(text)}")
    return "\n".join(lines)


def build_messages(jobs, name, reddit_posts=None, networking=None, max_len=3800):
    """Return a list of Telegram-ready HTML messages, each under the size limit."""
    groups = {k: [] for k, _ in BUCKETS}
    for j in jobs:
        groups[_bucket(j)].append(j)

    summary = " · ".join(
        f"{len(groups[k])} {label.split(' ', 1)[1]}" for k, label in BUCKETS if groups[k]
    )
    header = (
        f"👋 <b>{_esc(name)}'s opportunities</b> — {date.today().strftime('%d %b %Y')}\n"
        f"{len(jobs)} fresh · sustainability &amp; finance · India-first\n"
        + (f"<i>{summary}</i>\n" if summary else "")
    )

    # Each block is a small unit (section header or one item) so packing stays clean.
    blocks, idx = [], 1
    for key, label in BUCKETS:
        items = groups[key]
        if not items:
            continue
        blocks.append(f"— <b>{label}</b> —")
        for j in items:
            blocks.append(_format_job(idx, j))
            idx += 1
    if reddit_posts:
        blocks.extend(_reddit_block(reddit_posts))
    if networking and networking.get("links"):
        blocks.append(_networking_block(networking))

    messages, current = [], header
    for block in blocks:
        candidate = current + "\n" + block + "\n"
        if len(candidate) > max_len and current.strip():
            messages.append(current.rstrip())
            current = block + "\n"
        else:
            current = candidate
    if current.strip():
        messages.append(current.rstrip())
    return messages
