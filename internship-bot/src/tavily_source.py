"""Tavily web search — the 'grounding-style' source.

Tavily is a search API built for LLMs: it returns real, current web results
(title + url + snippet) for a query. That lets us surface live listings from
across the web — Internshala, LinkedIn, Naukri, company pages — with real links,
which is exactly what Gemini grounding was meant to do (minus the 429 quota).

Isolated and best-effort: any query failure just logs and is skipped.
"""
import urllib.parse

import requests

import boards  # reuse the shared domain-relevance filter (src/ is on sys.path)

UA = {"User-Agent": "internship-bot/1.0"}
TIMEOUT = 30
API = "https://api.tavily.com/search"


def _org_from_url(url: str) -> str:
    try:
        net = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
        name = net.split(".")[0] if net else ""
        return name.capitalize() if name else net
    except ValueError:
        return ""


def fetch(settings, profile: dict) -> list:
    key = settings.tavily_api_key
    if not key:
        print("[tavily] no TAVILY_API_KEY — skipping")
        return []
    cfg = profile.get("tavily", {}) or {}
    queries = cfg.get("queries", [])
    include = cfg.get("include_domains", []) or []
    max_results = cfg.get("max_results", 8)

    out, seen = [], set()
    for q in queries:
        body = {
            "api_key": key, "query": q, "search_depth": "basic",
            "max_results": max_results, "include_answer": False,
        }
        if include:
            body["include_domains"] = include
        try:
            r = requests.post(API, json=body, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            results = r.json().get("results", [])
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
            seen.add(url)
            snippet = content[:160] + ("…" if len(content) > 160 else "")
            out.append({
                "title": title, "org": _org_from_url(url),
                "location": "", "type": "", "link": url, "deadline": "",
                "why_fit": snippet, "source": "tavily",
            })
    print(f"[tavily] {len(out)} on-topic results")
    return out
