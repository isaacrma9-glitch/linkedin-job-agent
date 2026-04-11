import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

LINKEDIN_GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.linkedin.com/jobs/search/",
    "Connection": "keep-alive",
}


def fetch_jobs(keywords: str, location: str, max_results: int = 50) -> list[dict]:
    """
    Fetch jobs from LinkedIn's guest API endpoint.
    Returns a list of job dicts with title, company, location, url, and snippet.
    """
    jobs = []
    start = 0
    batch_size = 25

    while start < max_results:
        params = {
            "keywords": keywords,
            "location": location,
            "start": start,
            "pageNum": 0,
            "f_TPR": "r86400",  # Posted in last 24 hours
        }

        try:
            resp = requests.get(
                LINKEDIN_GUEST_API,
                params=params,
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Request failed for '{keywords}' in '{location}': {e}")
            break

        parsed = _parse_job_cards(resp.text)
        if not parsed:
            break

        jobs.extend(parsed)
        start += batch_size

        # Polite delay to avoid rate limiting
        time.sleep(random.uniform(1.5, 3.0))

    return jobs[:max_results]


def _parse_job_cards(html: str) -> list[dict]:
    """Parse LinkedIn job card HTML into structured dicts."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("li")
    jobs = []

    for card in cards:
        try:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            location_tag = card.find("span", class_="job-search-card__location")
            link_tag = card.find("a", class_="base-card__full-link")
            date_tag = card.find("time")
            snippet_tag = card.find("p", class_="job-search-card__snippet")

            if not title_tag or not link_tag:
                continue

            job = {
                "title": title_tag.get_text(strip=True),
                "company": company_tag.get_text(strip=True) if company_tag else "Unknown",
                "location": location_tag.get_text(strip=True) if location_tag else "Unknown",
                "url": link_tag.get("href", "").split("?")[0],
                "posted": date_tag.get("datetime", "") if date_tag else "",
                "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                "job_id": _extract_job_id(link_tag.get("href", "")),
            }
            jobs.append(job)
        except Exception as e:
            logger.debug(f"Failed to parse card: {e}")
            continue

    return jobs


def _extract_job_id(url: str) -> Optional[str]:
    """Extract LinkedIn job ID from URL for deduplication."""
    parts = url.rstrip("/").split("-")
    return parts[-1] if parts else None
