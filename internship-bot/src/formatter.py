"""Turns a ranked list of jobs into Telegram-ready HTML messages."""
import html
from datetime import date


def _esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def score(job: dict, keywords: list) -> int:
    """Simple relevance score: how many profile keywords the listing mentions,
    with a nudge toward sustainability/ESG and finance."""
    blob = " ".join(
        [job.get("title", ""), job.get("org", ""), job.get("why_fit", "")]
    ).lower()
    s = sum(1 for k in keywords if k.lower() in blob)
    for boost in ("esg", "sustainab", "climate", "carbon", "ghg", "finance"):
        if boost in blob:
            s += 1
    if "intern" in blob:
        s += 1
    return s


def _format_one(idx: int, job: dict) -> str:
    title = _esc(job.get("title", "Role"))
    org = _esc(job.get("org", ""))
    link = _esc(job.get("link", ""))
    head = f"<b>{idx}. {title}</b>"
    if org:
        head += f" — {org}"

    lines = [f'{head}\n<a href="{link}">Open listing</a>']
    meta = []
    if job.get("location"):
        meta.append(f"📍 {_esc(job['location'])}")
    if job.get("type"):
        meta.append(f"🗂 {_esc(job['type'])}")
    if job.get("deadline"):
        meta.append(f"⏳ {_esc(job['deadline'])}")
    if meta:
        lines.append("   ".join(meta))
    if job.get("why_fit"):
        lines.append(f"<i>Why it fits: {_esc(job['why_fit'])}</i>")
    return "\n".join(lines)


def build_messages(jobs: list, name: str, max_len: int = 3800) -> list:
    """Return a list of message strings, each under Telegram's 4096-char limit."""
    header = (
        f"👋 <b>{_esc(name)}'s daily opportunities</b> — "
        f"{date.today().strftime('%d %b %Y')}\n"
        f"{len(jobs)} fresh pick(s), curated for sustainability & finance.\n"
    )
    blocks = [_format_one(i + 1, j) for i, j in enumerate(jobs)]

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
