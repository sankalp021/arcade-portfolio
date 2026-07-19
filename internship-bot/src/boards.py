"""Secondary sources: real job-board APIs (no fragile HTML scraping).

- Remotive: free public JSON API, one call per search term.
- Greenhouse: public per-company board JSON (opt-in via profile.yaml).

We deliberately avoid scraping Internshala / LinkedIn / Naukri directly — they
block bots and it breaks constantly. Gemini's grounded search already surfaces
those listings (Google indexes them) with real links.
"""
import requests

UA = {"User-Agent": "internship-bot/1.0 (personal job digest)"}
TIMEOUT = 30


def _relevant(text: str, keywords: list) -> bool:
    low = (text or "").lower()
    return any(k.lower() in low for k in keywords)


def _remotive(searches: list, keywords: list, cap_per_search: int = 8) -> list:
    out = []
    for q in searches:
        try:
            r = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": q},
                headers=UA,
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            data = r.json().get("jobs", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[remotive:{q}] failed: {e}")
            continue
        kept = 0
        for j in data:
            title = j.get("title", "")
            if not _relevant(f"{title} {j.get('category', '')}", keywords):
                continue
            out.append(
                {
                    "title": title.strip(),
                    "org": (j.get("company_name") or "").strip(),
                    "location": (j.get("candidate_required_location") or "Remote").strip(),
                    "type": (j.get("job_type") or "").replace("_", "-").title(),
                    "link": (j.get("url") or "").strip(),
                    "deadline": "",
                    "why_fit": "",
                    "source": "remotive",
                }
            )
            kept += 1
            if kept >= cap_per_search:
                break
    print(f"[remotive] {len(out)} relevant openings")
    return out


def _greenhouse(tokens: list, keywords: list) -> list:
    out = []
    for token in tokens:
        try:
            r = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                headers=UA,
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            data = r.json().get("jobs", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[greenhouse:{token}] failed: {e}")
            continue
        for j in data:
            title = j.get("title", "")
            if not _relevant(title, keywords):
                continue
            loc = (j.get("location") or {}).get("name", "")
            out.append(
                {
                    "title": title.strip(),
                    "org": token,
                    "location": loc.strip(),
                    "type": "",
                    "link": (j.get("absolute_url") or "").strip(),
                    "deadline": "",
                    "why_fit": "",
                    "source": f"greenhouse:{token}",
                }
            )
    if tokens:
        print(f"[greenhouse] {len(out)} relevant openings")
    return out


def fetch(profile: dict) -> list:
    sources = profile.get("sources", {}) or {}
    keywords = profile.get("keywords", [])
    jobs = []
    jobs += _remotive(sources.get("remotive_searches", []), keywords)
    jobs += _greenhouse(sources.get("greenhouse_companies", []), keywords)
    # keep only entries with a usable link
    return [j for j in jobs if j.get("link", "").startswith("http")]
