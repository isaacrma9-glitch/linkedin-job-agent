"""
Score jobs based on how well they match Isaac's skills profile.
Higher score = better match.
"""

from profile import PROFILE


def score_job(job: dict) -> int:
    """
    Score a job 0-100 based on skill/keyword matches in title and snippet.
    Title matches are weighted 3x, snippet matches 1x.
    """
    skills = [s.lower() for s in PROFILE["skills"]]
    roles = [r.lower() for r in PROFILE["target_roles"]]

    title = job.get("title", "").lower()
    snippet = job.get("snippet", "").lower()
    company = job.get("company", "").lower()
    full_text = f"{title} {snippet} {company}"

    score = 0

    # Role match in title (high value)
    for role in roles:
        role_words = role.lower().split()
        if all(w in title for w in role_words):
            score += 30
            break
        elif any(w in title for w in role_words):
            score += 15

    # Skill matches
    matched_skills = set()
    for skill in skills:
        if skill in title:
            score += 6  # Title match worth more
            matched_skills.add(skill)
        elif skill in snippet:
            score += 2  # Snippet match
            matched_skills.add(skill)

    # Bonus for remote / Costa Rica
    locations = [loc.lower() for loc in PROFILE["locations"]]
    job_location = job.get("location", "").lower()
    if any(loc in job_location for loc in locations):
        score += 10

    return min(score, 100)


def enrich_jobs(jobs: list[dict]) -> list[dict]:
    """Add score to each job and filter by minimum threshold."""
    enriched = []
    for job in jobs:
        job["score"] = score_job(job)
        if job["score"] >= PROFILE["min_score"]:
            enriched.append(job)

    # Sort best matches first
    enriched.sort(key=lambda j: j["score"], reverse=True)
    return enriched
