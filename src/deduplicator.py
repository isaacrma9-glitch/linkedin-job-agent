"""
Tracks seen jobs to avoid re-notifying the same postings.
Persists state in data/seen_jobs.json.
"""

import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SEEN_FILE = DATA_DIR / "seen_jobs.json"


def load_seen_ids() -> set[str]:
    DATA_DIR.mkdir(exist_ok=True)
    if not SEEN_FILE.exists():
        return set()
    with open(SEEN_FILE, encoding="utf-8") as f:
        return set(json.load(f))


def save_seen_ids(ids: set[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(ids), f, indent=2)


def filter_new_jobs(jobs: list[dict]) -> list[dict]:
    """Return only jobs not previously seen, and update seen list."""
    seen = load_seen_ids()
    new_jobs = []

    for job in jobs:
        job_id = job.get("job_id") or job.get("url")
        if job_id and job_id not in seen:
            new_jobs.append(job)
            seen.add(job_id)

    if new_jobs:
        save_seen_ids(seen)

    return new_jobs
