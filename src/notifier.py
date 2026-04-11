"""
Sends job results to a Discord webhook as rich embeds.
"""

import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# Score color thresholds
COLORS = {
    80: 0x00FF88,   # Green — excellent match
    50: 0xFFAA00,   # Orange — good match
    0:  0x4A90D9,   # Blue — partial match
}


def _score_color(score: int) -> int:
    for threshold, color in COLORS.items():
        if score >= threshold:
            return color
    return 0x4A90D9


def _build_embed(job: dict) -> dict:
    score = job.get("score", 0)
    return {
        "title": f"{job['title']} @ {job['company']}",
        "url": job.get("url", ""),
        "description": job.get("snippet", "")[:300] or "_Sin descripción disponible_",
        "color": _score_color(score),
        "fields": [
            {"name": "Ubicacion", "value": job.get("location", "N/A"), "inline": True},
            {"name": "Match Score", "value": f"{score}/100", "inline": True},
            {"name": "Publicado", "value": job.get("posted", "N/A"), "inline": True},
        ],
        "footer": {"text": "LinkedIn Job Agent"},
    }


def send_discord_report(jobs: list[dict]) -> None:
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set — skipping notification")
        return

    if not jobs:
        _send_message(":white_check_mark: No hay nuevas ofertas relevantes hoy.")
        return

    # Header message
    now = datetime.utcnow().strftime("%Y-%m-%d")
    _send_message(f":briefcase: **{len(jobs)} nueva(s) oferta(s) encontradas** — {now}")

    # Send up to 10 jobs as embeds (Discord limit)
    for job in jobs[:10]:
        payload = {"embeds": [_build_embed(job)]}
        try:
            resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send embed for '{job['title']}': {e}")

    if len(jobs) > 10:
        _send_message(f"_... y {len(jobs) - 10} más. Revisa el log completo._")


def _send_message(content: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    except requests.RequestException as e:
        logger.error(f"Failed to send message: {e}")
