"""Tavily web search — the 'grounding-style' source.

Tavily is a search API built for LLMs: it returns real, current web results
(title + url + snippet) for a query. That lets us surface live listings from
across the web — Internshala, LinkedIn, Naukri, company pages — with real links,
which is exactly what Gemini grounding was meant to do (minus the 429 quota).

Isolated and best-effort: any query failure just logs and is skipped.
"""
import re
import urllib.parse

import requests

import boards  # reuse the shared domain-relevance filter (src/ is on sys.path)

UA = {"User-Agent": "internship-bot/1.0"}
TIMEOUT = 30
API = "https://api.tavily.com/search"


# Subdomain prefixes to strip so "in.linkedin.com" -> LinkedIn, not "In".
_SUBDOMAINS = {"www", "in", "fr", "uk", "us", "en", "eu", "jobs", "careers", "apply", "m"}
_PRETTY = {
    "linkedin": "LinkedIn", "glassdoor": "Glassdoor", "naukri": "Naukri", "indeed": "Indeed",
    "foundit": "Foundit", "internshala": "Internshala", "impactpool": "Impactpool",
    "climatechangecareers": "Climate Change Careers", "terra": "Terra.do",
}

# Aggregator / search-index pages ("24 ESG intern jobs", "82 BRSR Job Vacancies").
_INDEX_RE = re.compile(r"\b\d[\d,]*\s+[\w &.,/'+-]*?\b(jobs?|vacanc|internships?|openings?|positions?)\b", re.I)
_INDEX_WORDS = ("jobs, employment", "job vacancies", "latest vacancies", "jobs available", "browse jobs")
_INDEX_URL = ("srch_", "/q-", "-jobs.html", "-jobs-in-", "/jobs-in-", "/brsr-jobs")


def _org_from_url(url: str) -> str:
    try:
        net = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return ""
    labels = [x for x in net.split(".") if x]
    while labels and labels[0] in _SUBDOMAINS:
        labels.pop(0)
    name = labels[0] if labels else net
    return _PRETTY.get(name, name.capitalize())


def _looks_like_index(title: str, url: str) -> bool:
    """True for search-result / listing-index pages rather than a single opening."""
    t = (title or "").lower()
    if _INDEX_RE.search(title or ""):
        return True
    if any(w in t for w in _INDEX_WORDS):
        return True
    return any(m in (url or "").lower() for m in _INDEX_URL)


# Reddit post filtering: keep genuine hiring/opportunity posts, drop the noise
# (people seeking jobs, advice threads, bare subreddit links).
_SEEKER_HINTS = (
    "looking for", "need a", "need an", "advice", "guidance", "how do i", "how to",
    "help me", "resume", "any leads", "suggestion", "should i", "is it worth",
    "chances", "review my", "am i", "roast my",
)
_HIRING_HINTS = (
    "hiring", "we're looking", "we are looking", "join our", "join us", "opening",
    "vacancy", "vacancies", "recruit", "apply now", "now hiring", "we are hiring",
    "seeking a", "seeking an", "position open",
)


def _is_opportunity(title: str) -> bool:
    t = (title or "").lower()
    if any(s in t for s in _SEEKER_HINTS):
        return False
    return any(h in t for h in _HIRING_HINTS)


def _subreddit(url: str) -> str:
    try:
        parts = urllib.parse.urlparse(url).path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "r":
            return f"r/{parts[1]}"
    except ValueError:
        pass
    return "reddit"


def _search(key: str, query: str, max_results: int, include: list) -> list:
    body = {
        "api_key": key, "query": query, "search_depth": "basic",
        "max_results": max_results, "include_answer": False,
    }
    if include:
        body["include_domains"] = include
    r = requests.post(API, json=body, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("results", [])


def fetch_reddit(settings, profile: dict) -> list:
    """A focused Reddit search via Tavily (Reddit blocks anon CI requests).
    ~1 credit per configured query. Returns items shaped like Reddit posts."""
    key = settings.tavily_api_key
    cfg = profile.get("tavily", {}) or {}
    queries = cfg.get("reddit_queries", [])
    if not key or not queries:
        return []
    out, seen = [], set()
    for q in queries:
        try:
            results = _search(key, q, cfg.get("max_results", 6), ["reddit.com"])
        except (requests.RequestException, ValueError) as e:
            print(f"[tavily-reddit:{q[:30]}] failed: {e}")
            continue
        for res in results:
            title = (res.get("title") or "").strip()
            url = (res.get("url") or "").strip()
            if not title or not url.startswith("http") or url in seen:
                continue
            if "/comments/" not in url:            # must be a real post, not a bare subreddit
                continue
            if not boards.domain_relevant(title, res.get("content", "")):
                continue
            if not _is_opportunity(title):         # a hiring post, not a seeker/advice thread
                continue
            seen.add(url)
            out.append({
                "title": title, "org": _subreddit(url), "location": "",
                "type": "reddit", "link": url, "deadline": "", "why_fit": "",
                "posted": "", "source": "reddit",
            })
    print(f"[tavily-reddit] {len(out)} posts")
    return out


def fetch(settings, profile: dict, max_queries: int = None) -> list:
    key = settings.tavily_api_key
    if not key:
        print("[tavily] no TAVILY_API_KEY — skipping")
        return []
    cfg = profile.get("tavily", {}) or {}
    queries = cfg.get("queries", [])
    if max_queries is None:
        max_queries = cfg.get("max_queries_per_run", 3)
    queries = queries[:max_queries]  # cap credit use (each query = 1 credit)
    include = cfg.get("include_domains", []) or []
    max_results = cfg.get("max_results", 8)

    out, seen = [], set()
    for q in queries:
        try:
            results = _search(key, q, max_results, include)
        except (requests.RequestException, ValueError) as e:
            print(f"[tavily:{q[:30]}] failed: {e}")
            continue
        for res in results:
            title = (res.get("title") or "").strip()
            url = (res.get("url") or "").strip()
            content = (res.get("content") or "").strip()
            if not title or not url.startswith("http") or url in seen:
                continue
            if not boards.domain_relevant(title, content):
                continue
            if _looks_like_index(title, url) or "closed" in content.lower():
                continue  # skip search-index pages and expired postings
            seen.add(url)
            snippet = content[:160] + ("…" if len(content) > 160 else "")
            out.append({
                "title": title, "org": _org_from_url(url),
                "location": "", "type": "", "link": url, "deadline": "",
                "why_fit": snippet, "posted": "", "source": "tavily",
            })
    print(f"[tavily] {len(out)} on-topic results")
    return out
