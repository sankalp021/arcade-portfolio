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
                "deadline": "", "why_fit": "", "posted": j.get("publication_date", ""),
                "source": "remotive",
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
                "deadline": "", "why_fit": "", "posted": j.get("created", ""),
                "source": "adzuna",
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
            "deadline": "", "why_fit": "", "posted": j.get("publication_date", ""),
            "source": "themuse",
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
                "deadline": "", "why_fit": "", "posted": _text(j.get("pubDate")),
                "source": "jobicy",
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
                "deadline": "", "why_fit": "", "posted": j.get("updated_at", ""),
                "source": f"greenhouse:{token}",
            })
    if tokens:
        print(f"[greenhouse] {len(out)} on-topic openings")
    return out


def _lever(companies: list) -> list:
    out = []
    for c in companies:
        try:
            r = requests.get(f"https://api.lever.co/v0/postings/{c}",
                             params={"mode": "json"}, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"[lever:{c}] failed: {e}")
            continue
        for j in (data or []):
            cats = j.get("categories", {}) or {}
            title = j.get("text", "")
            if not domain_relevant(title, cats.get("team"), cats.get("department")):
                continue
            out.append({
                "title": _text(title), "org": c,
                "location": _text(cats.get("location")),
                "type": _text(cats.get("commitment")),
                "link": _text(j.get("hostedUrl")),
                "deadline": "", "why_fit": "", "posted": j.get("createdAt", ""),
                "source": f"lever:{c}",
            })
    if companies:
        print(f"[lever] {len(out)} on-topic openings")
    return out


def _ashby(orgs: list) -> list:
    out = []
    for org in orgs:
        try:
            r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{org}",
                             headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json().get("jobs", [])
        except (requests.RequestException, ValueError) as e:
            print(f"[ashby:{org}] failed: {e}")
            continue
        for j in data:
            title = j.get("title", "")
            if not domain_relevant(title, j.get("department"), j.get("team")):
                continue
            out.append({
                "title": _text(title), "org": org,
                "location": _text(j.get("location")),
                "type": _text(j.get("employmentType")),
                "link": _text(j.get("jobUrl") or j.get("applyUrl")),
                "deadline": "", "why_fit": "", "posted": _text(j.get("publishedAt")),
                "source": f"ashby:{org}",
            })
    if orgs:
        print(f"[ashby] {len(out)} on-topic openings")
    return out


def _unstop(types: list, searches: list) -> list:
    """Unstop (Indian internships/jobs/competitions) via its unofficial public
    search endpoint. Best-effort: undocumented, so it's fully isolated."""
    out, seen = [], set()
    headers = {**UA, "Accept": "application/json"}
    for t in types:
        for q in (searches or [""]):
            try:
                r = requests.get(
                    "https://unstop.com/api/public/opportunity/search-result",
                    params={"opportunity": t, "per_page": 15, "oppstatus": "open",
                            "searchTerm": q},
                    headers=headers, timeout=TIMEOUT,
                )
                r.raise_for_status()
                payload = r.json()
            except (requests.RequestException, ValueError) as e:
                print(f"[unstop:{t}:{q}] failed: {e}")
                continue
            node = payload.get("data", payload)
            listings = node.get("data") if isinstance(node, dict) else node
            if not isinstance(listings, list):
                continue
            for j in listings:
                title = j.get("title", "")
                if not domain_relevant(title):
                    continue
                url = j.get("public_url") or j.get("seo_url") or j.get("url") or ""
                if url and not url.startswith("http"):
                    url = "https://unstop.com/" + url.lstrip("/")
                org = (j.get("organisation") or {}).get("name") or j.get("organisation_name") or ""
                key = (title, org)
                if not url.startswith("http") or key in seen:
                    continue
                seen.add(key)
                out.append({
                    "title": _text(title), "org": _text(org),
                    "location": "India", "type": _text(t),
                    "link": _text(url), "deadline": "", "why_fit": "",
                    "posted": _text(j.get("start_date") or j.get("created") or j.get("updated_at")),
                    "source": "unstop",
                })
    print(f"[unstop] {len(out)} on-topic openings")
    return out


def _workday(boards: list, searches: list) -> list:
    """Query big-company Workday career sites via their per-tenant CXS JSON.
    Each board is {host, tenant, site} from a company's careers URL, e.g.
    https://<tenant>.wd5.myworkdayjobs.com/en-US/<site> -> host=<tenant>.wd5....,
    tenant=<tenant>, site=<site>."""
    out, seen = [], set()
    headers = {**UA, "Content-Type": "application/json", "Accept": "application/json"}
    for b in boards:
        host, tenant, site = b.get("host"), b.get("tenant"), b.get("site")
        if not (host and tenant and site):
            continue
        for q in (searches or [""]):
            try:
                r = requests.post(
                    f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                    json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q},
                    headers=headers, timeout=TIMEOUT,
                )
                r.raise_for_status()
                postings = r.json().get("jobPostings", [])
            except (requests.RequestException, ValueError) as e:
                print(f"[workday:{tenant}:{q}] failed: {e}")
                continue
            for j in postings:
                title = j.get("title", "")
                ext = j.get("externalPath", "")
                if not title or not ext or not domain_relevant(title):
                    continue
                if ext in seen:
                    continue
                seen.add(ext)
                out.append({
                    "title": _text(title), "org": tenant,
                    "location": _text(j.get("locationsText")),
                    "type": "", "link": f"https://{host}/en-US/{site}{ext}",
                    "deadline": "", "why_fit": "", "posted": _text(j.get("postedOn")),
                    "source": f"workday:{tenant}",
                })
    if boards:
        print(f"[workday] {len(out)} on-topic openings")
    return out


def fetch(profile: dict, settings) -> list:
    s = profile.get("sources", {}) or {}
    terms = s.get("adzuna_searches", [])
    # Each source is isolated: a failure in one never aborts the whole digest.
    providers = [
        lambda: _adzuna(s.get("adzuna_country", "in"), terms,
                        settings.adzuna_app_id, settings.adzuna_app_key),
        lambda: _remotive(s.get("remotive_searches", [])),
        lambda: _the_muse(s.get("the_muse_categories", []), s.get("the_muse_location", "")),
        lambda: _jobicy(s.get("jobicy_tags", [])),
        lambda: _greenhouse(s.get("greenhouse_companies", [])),
        lambda: _lever(s.get("lever_companies", [])),
        lambda: _ashby(s.get("ashby_orgs", [])),
        lambda: _unstop(s.get("unstop_types", []), terms),
        lambda: _workday(s.get("workday_boards", []), terms),
    ]
    jobs = []
    for provider in providers:
        try:
            jobs += provider()
        except Exception as e:  # noqa: BLE001 - never let one source crash the run
            print(f"[boards] source error: {e}")
    return [j for j in jobs if j.get("link", "").startswith("http")]
