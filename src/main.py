"""
LinkedIn Job Agent — Entry point
Searches LinkedIn for jobs matching Isaac's profile, scores them,
filters duplicates, and sends new matches to Discord.
"""

import logging
import sys
import os

# Allow running from src/ or project root
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from profile import SEARCH_QUERIES, PROFILE
from job_searcher import fetch_jobs
from scorer import enrich_jobs
from deduplicator import filter_new_jobs
from notifier import send_discord_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run():
    logger.info("Starting LinkedIn Job Agent...")
    all_jobs = []

    for query in SEARCH_QUERIES:
        keywords = query["keywords"]
        location = query["location"]
        logger.info(f"Searching: '{keywords}' in '{location}'")

        jobs = fetch_jobs(keywords, location, max_results=PROFILE["max_results"])
        logger.info(f"  Found {len(jobs)} raw results")
        all_jobs.extend(jobs)

    # Deduplicate by job_id across queries
    seen_ids = set()
    unique_jobs = []
    for job in all_jobs:
        jid = job.get("job_id") or job.get("url")
        if jid not in seen_ids:
            seen_ids.add(jid)
            unique_jobs.append(job)

    logger.info(f"Unique jobs after cross-query dedup: {len(unique_jobs)}")

    # Score and filter by skill match
    scored_jobs = enrich_jobs(unique_jobs)
    logger.info(f"Jobs above score threshold: {len(scored_jobs)}")

    # Filter out previously seen jobs
    new_jobs = filter_new_jobs(scored_jobs)
    logger.info(f"New jobs (not seen before): {len(new_jobs)}")

    # Send to Discord
    send_discord_report(new_jobs)

    if new_jobs:
        logger.info("Top matches:")
        for job in new_jobs[:5]:
            logger.info(f"  [{job['score']}/100] {job['title']} @ {job['company']} — {job['location']}")
    else:
        logger.info("No new relevant jobs found today.")


if __name__ == "__main__":
    run()
