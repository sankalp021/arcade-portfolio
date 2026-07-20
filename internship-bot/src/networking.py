"""Curated LinkedIn search deep-links + connection-note templates.

Honest by design: we do NOT invent people or scrape profiles. Each link opens a
real LinkedIn search (people or jobs) pre-filtered to her targets, so she lands
on a live list of actual recruiters/alumni/roles to send requests to.
"""
import urllib.parse


def _people_url(keywords: str) -> str:
    return ("https://www.linkedin.com/search/results/people/?keywords="
            + urllib.parse.quote(keywords))


def _jobs_url(keywords: str, location: str) -> str:
    params = {
        "keywords": keywords,
        "location": location or "India",
        "f_JT": "I",        # job type: Internship
        "f_E": "1,2",       # experience: Internship, Entry level
        "sortBy": "DD",     # most recent first
    }
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)


NOTE_TEMPLATES = [
    ("Recruiter", "Hi {name}, I'm an MBA (Sustainability Management) student at "
     "IIFM Bhopal with ESG/GHG data-analysis experience, exploring winter "
     "internship & placement roles in sustainability/finance. Would love to connect."),
    ("Alum / peer", "Hi {name}, fellow IIFM/sustainability path here — I'd love "
     "to connect and learn from your journey into ESG/sustainable finance."),
]


def build(profile: dict) -> dict:
    net = profile.get("networking", {}) or {}
    location = net.get("linkedin_location", "India")
    max_links = net.get("max_links", 6)

    links = []
    for q in net.get("linkedin_people_searches", []):
        links.append({"kind": "people", "label": q, "url": _people_url(q)})
    for q in net.get("linkedin_job_searches", []):
        links.append({"kind": "jobs", "label": f"{q} (internship, {location})",
                      "url": _jobs_url(q, location)})

    return {"links": links[:max_links], "note_templates": NOTE_TEMPLATES}
