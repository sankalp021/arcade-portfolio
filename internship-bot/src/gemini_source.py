"""Primary source: Gemini with Google Search grounding.

Grounding is what makes this trustworthy — the model runs live Google searches
and answers from *current* results (with real source links) instead of
hallucinating job postings from stale training data.
"""
import json
import re


def _build_prompt(profile: dict, n: int) -> str:
    p = profile
    person = p.get("person", {})
    target = p.get("target", {})
    roles = "; ".join(target.get("roles", []))
    locations = ", ".join(target.get("locations", []))
    skills = "; ".join(p.get("skills", []))
    notes = " ".join(p.get("notes", []))
    return f"""You are a job-hunting research assistant. Use Google Search to find \
REAL, CURRENTLY-OPEN internship and early-career openings for this candidate.

CANDIDATE
- {person.get('headline', '')}
- Looking for: {target.get('timeframe', '')}
- Target roles: {roles}
- Preferred locations: {locations}
- Key skills: {skills}
- Extra context: {notes}

RULES
- Only list openings that appear to be OPEN right now (search for recent postings).
- Prefer India-based or remote roles; sustainability/ESG and finance are both in scope.
- Include the direct application/listing URL you actually found via search.
- Do NOT invent companies, roles, or links. If unsure a link is real, skip it.
- Aim for up to {n} distinct openings across different companies.

OUTPUT
Return ONLY a JSON array (no prose, no markdown fences). Each element:
{{
  "title": "role title",
  "org": "company/organization",
  "location": "city/remote",
  "type": "Internship" or "Full-time",
  "link": "https://... direct listing",
  "deadline": "date if known, else empty string",
  "why_fit": "one short sentence tying it to her ESG/finance/data background"
}}"""


def _extract_json_array(text: str):
    """Tolerantly pull a JSON array out of the model's text."""
    if not text:
        return []
    t = text.strip()
    # strip ```json ... ``` fences if present
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    try:
        data = json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("["), t.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            data = json.loads(t[start : end + 1])
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def fetch(settings, profile: dict, n: int = 12) -> list:
    if not settings.gemini_api_key:
        print("[gemini] no GEMINI_API_KEY set — skipping grounded search")
        return []
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        print(f"[gemini] SDK not installed: {e}")
        return []

    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=_build_prompt(profile, n),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            ),
        )
    except Exception as e:  # noqa: BLE001 - never let one source crash the run
        print(f"[gemini] request failed: {e}")
        return []

    raw = _extract_json_array(getattr(resp, "text", "") or "")
    jobs = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        link = (item.get("link") or "").strip()
        title = (item.get("title") or "").strip()
        if not title or not link.startswith("http"):
            continue
        jobs.append(
            {
                "title": title,
                "org": (item.get("org") or "").strip(),
                "location": (item.get("location") or "").strip(),
                "type": (item.get("type") or "").strip(),
                "link": link,
                "deadline": (item.get("deadline") or "").strip(),
                "why_fit": (item.get("why_fit") or "").strip(),
                "source": "gemini",
            }
        )
    print(f"[gemini] {len(jobs)} openings from grounded search")
    return jobs
