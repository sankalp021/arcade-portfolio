"""Secondary sources: real job-board APIs (no fragile HTML scraping).

- Adzuna:    free API with genuine India coverage (needs free app id/key).
- Remotive:  free public JSON API, one call per search term.
- The Muse:  free public API (no key), supports location + category.
- Jobicy:    free remote-jobs API (no key).
- Greenhouse: public per-company board JSON (opt-in via profile.yaml).

We deliberately avoid scraping Internshala / LinkedIn / Naukri directly — they
block bots and it breaks constantly.
"""
import requests

UA = {"User-Agent": "internship-bot/1.0 (personal job digest)"}
TIMEOUT = 30

# A listing must mention at least one of these to count as on-topic. Plain
# "analyst"/"data"/"intern" alone is NOT enough — that's what let a French-language
# data-analyst gig in Canada slip through before.
DOMAIN_TERMS = (
    "esg", "sustainab", "climate", "carbon", "ghg", "brsr", "decarbon",
    "environment", "renewable", "finance", "financial", "investment",
    "equity research", "fp&a", "impact",
)


def _text(v, default: str = "") -> str:
    """Coerce a possibly-list/None API field into a clean string."""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v if x)
    if v is None:
        return default
    return str(v).strip()


def domain_relevant(*texts) -> bool:
    # Robust to non-string values (some APIs return lists, e.g. Jobicy jobIndustry).
    parts = []
    for t in texts:
        if isinstance(t, (list, tuple)):
            parts.append(" ".join(str(x) for x in t))
        elif t:
            parts.append(str(t))
    blob = " ".join(parts).lower()
    return any(term in blob for term in DOMAIN_TERMS)


def _remotive(searches: list, cap_per_search: int = 8) -> list:
    out = []
    for q in searches:
        try:
            r = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": q}, headers=UA, timeout=TIMEOUT,
            )
            r.raise_for_status()
            data = r.json().get("jobs", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[remotive:{q}] failed: {e}")
            continue
        kept = 0
        for j in data:
            title = j.get("title", "")
            if not domain_relevant(title, j.get("category", "")):
                continue
            out.append({
                "title": title.strip(),
                "org": (j.get("company_name") or "").strip(),
                "location": (j.get("candidate_required_location") or "Remote").strip(),
                "type": (j.get("job_type") or "").replace("_", "-").title(),
                "link": (j.get("url") or "").strip(),
                "deadline": "", "why_fit": "", "source": "remotive",
            })
            kept += 1
            if kept >= cap_per_search:
                break
    print(f"[remotive] {len(out)} on-topic openings")
    return out


def _adzuna(country: str, searches: list, app_id: str, app_key: str) -> list:
    if not app_id or not app_key:
        print("[adzuna] no ADZUNA_APP_ID/ADZUNA_APP_KEY — skipping (India coverage off)")
        return []
    out = []
    for q in searches:
        try:
            r = requests.get(
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
                params={
                    "app_id": app_id, "app_key": app_key, "what": q,
                    "results_per_page": 10, "content-type": "application/json",
                },
                headers=UA, timeout=TIMEOUT,
            )
            r.raise_for_status()
            data = r.json().get("results", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[adzuna:{q}] failed: {e}")
            continue
        for j in data:
            title = j.get("title", "")
            if not domain_relevant(title, j.get("description", "")):
                continue
            out.append({
                "title": title.strip(),
                "org": ((j.get("company") or {}).get("display_name") or "").strip(),
                "location": ((j.get("location") or {}).get("display_name") or "").strip(),
                "type": (j.get("contract_time") or "").replace("_", "-").title(),
                "link": (j.get("redirect_url") or "").strip(),
                "deadline": "", "why_fit": "", "source": "adzuna",
            })
    print(f"[adzuna] {len(out)} on-topic openings")
    return out


def _the_muse(categories: list, location: str) -> list:
    params = [("page", 1)]
    for c in categories:
        params.append(("category", c))
    if location:
        params.append(("location", location))
    try:
        r = requests.get(
            "https://www.themuse.com/api/public/jobs",
            params=params, headers=UA, timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json().get("results", [])
    except (requests.RequestException, ValueError) as e:
        print(f"[themuse] failed: {e}")
        return []
    out = []
    for j in data:
        title = j.get("name", "")
        if not domain_relevant(title):
            continue
        locs = ", ".join(l.get("name", "") for l in (j.get("locations") or []))
        out.append({
            "title": title.strip(),
            "org": ((j.get("company") or {}).get("name") or "").strip(),
            "location": locs.strip(),
            "type": (j.get("level") or "").strip(),
            "link": ((j.get("refs") or {}).get("landing_page") or "").strip(),
            "deadline": "", "why_fit": "", "source": "themuse",
        })
    print(f"[themuse] {len(out)} on-topic openings")
    return out


def _jobicy(tags: list, cap: int = 10) -> list:
    out = []
    for tag in tags:
        try:
            r = requests.get(
                "https://jobicy.com/api/v2/remote-jobs",
                params={"count": 20, "tag": tag}, headers=UA, timeout=TIMEOUT,
            )
            r.raise_for_status()
            data = r.json().get("jobs", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[jobicy:{tag}] failed: {e}")
            continue
        kept = 0
        for j in data:
            title = j.get("jobTitle", "")
            if not domain_relevant(title, j.get("jobIndustry", "")):
                continue
            out.append({
                "title": _text(title),
                "org": _text(j.get("companyName")),
                "location": _text(j.get("jobGeo")) or "Remote",
                "type": _text(j.get("jobType")),
                "link": _text(j.get("url")),
                "deadline": "", "why_fit": "", "source": "jobicy",
            })
            kept += 1
            if kept >= cap:
                break
    print(f"[jobicy] {len(out)} on-topic openings")
    return out


def _greenhouse(tokens: list) -> list:
    out = []
    for token in tokens:
        try:
            r = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                headers=UA, timeout=TIMEOUT,
            )
            r.raise_for_status()
            data = r.json().get("jobs", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[greenhouse:{token}] failed: {e}")
            continue
        for j in data:
            title = j.get("title", "")
            if not domain_relevant(title):
                continue
            out.append({
                "title": title.strip(), "org": token,
                "location": ((j.get("location") or {}).get("name") or "").strip(),
                "type": "", "link": (j.get("absolute_url") or "").strip(),
                "deadline": "", "why_fit": "", "source": f"greenhouse:{token}",
            })
    if tokens:
        print(f"[greenhouse] {len(out)} on-topic openings")
    return out


def fetch(profile: dict, settings) -> list:
    s = profile.get("sources", {}) or {}
    # Each source is isolated: a failure in one never aborts the whole digest.
    providers = [
        lambda: _adzuna(s.get("adzuna_country", "in"), s.get("adzuna_searches", []),
                        settings.adzuna_app_id, settings.adzuna_app_key),
        lambda: _remotive(s.get("remotive_searches", [])),
        lambda: _the_muse(s.get("the_muse_categories", []), s.get("the_muse_location", "")),
        lambda: _jobicy(s.get("jobicy_tags", [])),
        lambda: _greenhouse(s.get("greenhouse_companies", [])),
    ]
    jobs = []
    for provider in providers:
        try:
            jobs += provider()
        except Exception as e:  # noqa: BLE001 - never let one source crash the run
            print(f"[boards] source error: {e}")
    return [j for j in jobs if j.get("link", "").startswith("http")]
