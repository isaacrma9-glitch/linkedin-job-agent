"""
Sends job results to a Discord webhook as rich embeds.
"""

import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
DISCORD_API = "https://discord.com/api/v10"

COLORS = {
    80: 0x00FF88,
    50: 0xFFAA00,
    0:  0x4A90D9,
}


def _headers() -> dict:
    return {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}


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
        "description": job.get("snippet", "")[:300] or "_Sin descripcion disponible_",
        "color": _score_color(score),
        "fields": [
            {"name": "Ubicacion", "value": job.get("location", "N/A"), "inline": True},
            {"name": "Match Score", "value": f"{score}/100", "inline": True},
            {"name": "Publicado", "value": job.get("posted", "N/A"), "inline": True},
        ],
        "footer": {"text": "LinkedIn Job Agent"},
    }


def _post(payload: dict) -> None:
    if not DISCORD_BOT_TOKEN or not DISCORD_CHANNEL_ID:
        logger.warning("DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID not set — skipping")
        return
    url = f"{DISCORD_API}/channels/{DISCORD_CHANNEL_ID}/messages"
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Discord API error: {e}")


def send_discord_report(jobs: list[dict]) -> None:
    if not jobs:
        _post({"content": ":white_check_mark: No hay nuevas ofertas relevantes hoy."})
        return

    now = datetime.utcnow().strftime("%Y-%m-%d")
    _post({"content": f":briefcase: **{len(jobs)} nueva(s) oferta(s) encontradas** — {now}"})

    for job in jobs[:10]:
        _post({"embeds": [_build_embed(job)]})

    if len(jobs) > 10:
        _post({"content": f"_... y {len(jobs) - 10} mas. Revisa el log completo._"})
