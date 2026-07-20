"""Turns ranked jobs + Reddit posts + networking links into Telegram HTML messages."""
import html
from datetime import date


def _esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def score(job: dict, keywords: list) -> int:
    """Relevance score: profile-keyword hits, nudged toward her core domains."""
    blob = " ".join([job.get("title", ""), job.get("org", ""), job.get("why_fit", "")]).lower()
    s = sum(1 for k in keywords if k.lower() in blob)
    for boost in ("esg", "sustainab", "climate", "carbon", "ghg", "finance", "investment"):
        if boost in blob:
            s += 1
    if "intern" in blob:
        s += 1
    return s


def _format_job(idx: int, job: dict) -> str:
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


def _format_reddit_block(posts: list) -> str:
    lines = ["👾 <b>From Reddit</b> <i>(recent, unverified — skim these)</i>"]
    for p in posts:
        lines.append(f'• <a href="{_esc(p.get("link",""))}">{_esc(p.get("title","(post)"))}</a>'
                     f' <i>{_esc(p.get("org",""))}</i>')
    return "\n".join(lines)


def _format_networking_block(networking: dict) -> str:
    lines = ["🌐 <b>Networking — LinkedIn</b> <i>(open & send connection requests)</i>"]
    for item in networking.get("links", []):
        tag = "🧑‍💼" if item.get("kind") == "people" else "💼"
        lines.append(f'{tag} <a href="{_esc(item.get("url",""))}">{_esc(item.get("label",""))}</a>')
    templates = networking.get("note_templates", [])
    if templates:
        lines.append("<i>Connection-note templates:</i>")
        for label, text in templates:
            lines.append(f"<i>· {_esc(label)}:</i> {_esc(text)}")
    return "\n".join(lines)


def build_messages(jobs, name, reddit_posts=None, networking=None, max_len=3800):
    """Return a list of message strings, each under Telegram's 4096-char limit."""
    n_jobs = len(jobs)
    if n_jobs:
        intro = f"{n_jobs} fresh role(s), curated for sustainability & finance."
    else:
        intro = "No brand-new roles today — but here's networking & Reddit to work on."
    header = (
        f"👋 <b>{_esc(name)}'s daily opportunities</b> — "
        f"{date.today().strftime('%d %b %Y')}\n{intro}\n"
    )

    blocks = [_format_job(i + 1, j) for i, j in enumerate(jobs)]
    if reddit_posts:
        blocks.append(_format_reddit_block(reddit_posts))
    if networking and networking.get("links"):
        blocks.append(_format_networking_block(networking))

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
