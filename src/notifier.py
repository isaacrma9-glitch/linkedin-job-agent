"""
Sends job results via Discord (bot API) and Gmail (SMTP).
"""

import os
import smtplib
import requests
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
DISCORD_API = "https://discord.com/api/v10"

# Gmail
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

COLORS = {80: 0x00FF88, 50: 0xFFAA00, 0: 0x4A90D9}


# ── Discord ──────────────────────────────────────────────────────────────────

def _discord_headers() -> dict:
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


def _discord_post(payload: dict) -> None:
    if not DISCORD_BOT_TOKEN or not DISCORD_CHANNEL_ID:
        return
    url = f"{DISCORD_API}/channels/{DISCORD_CHANNEL_ID}/messages"
    try:
        resp = requests.post(url, json=payload, headers=_discord_headers(), timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Discord API error: {e}")


def send_discord_report(jobs: list[dict]) -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d")
    if not jobs:
        _discord_post({"content": ":white_check_mark: No hay nuevas ofertas relevantes hoy."})
        return

    _discord_post({"content": f":briefcase: **{len(jobs)} oferta(s) nuevas** — {now}"})
    for job in jobs[:10]:
        _discord_post({"embeds": [_build_embed(job)]})
    if len(jobs) > 10:
        _discord_post({"content": f"_... y {len(jobs) - 10} mas en el correo de Gmail._"})


# ── Gmail ─────────────────────────────────────────────────────────────────────

def _build_html_email(jobs: list[dict]) -> str:
    now = datetime.utcnow().strftime("%d/%m/%Y")
    rows = ""
    for i, job in enumerate(jobs, 1):
        score = job.get("score", 0)
        if score >= 80:
            badge_color = "#00C97A"
        elif score >= 50:
            badge_color = "#F59E0B"
        else:
            badge_color = "#4A90D9"

        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
          <td style="padding:12px 8px;font-size:13px;color:#6b7280;text-align:center;">{i}</td>
          <td style="padding:12px 8px;">
            <a href="{job.get('url','#')}" style="font-weight:600;color:#111827;text-decoration:none;font-size:14px;">
              {job['title']}
            </a><br>
            <span style="color:#6b7280;font-size:12px;">{job['company']} · {job.get('location','')}</span>
          </td>
          <td style="padding:12px 8px;font-size:12px;color:#6b7280;">{job.get('posted','')}</td>
          <td style="padding:12px 8px;text-align:center;">
            <span style="background:{badge_color};color:#fff;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:700;">
              {score}/100
            </span>
          </td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif;">
      <div style="max-width:700px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <div style="background:#0A66C2;padding:28px 32px;">
          <h1 style="margin:0;color:#fff;font-size:22px;">💼 Ofertas Laborales — {now}</h1>
          <p style="margin:6px 0 0;color:#bfdbfe;font-size:14px;">{len(jobs)} ofertas nuevas encontradas en LinkedIn</p>
        </div>
        <div style="padding:24px 32px;">
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="background:#f9fafb;">
                <th style="padding:10px 8px;font-size:12px;color:#9ca3af;text-align:center;">#</th>
                <th style="padding:10px 8px;font-size:12px;color:#9ca3af;text-align:left;">Puesto / Empresa</th>
                <th style="padding:10px 8px;font-size:12px;color:#9ca3af;">Publicado</th>
                <th style="padding:10px 8px;font-size:12px;color:#9ca3af;">Match</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        <div style="padding:16px 32px;background:#f9fafb;text-align:center;font-size:12px;color:#9ca3af;">
          LinkedIn Job Agent · Martes y Jueves · isaac.rma9@gmail.com
        </div>
      </div>
    </body>
    </html>"""


def send_email_report(jobs: list[dict]) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logger.warning("GMAIL_USER or GMAIL_APP_PASSWORD not set — skipping email")
        return

    now = datetime.utcnow().strftime("%d/%m/%Y")
    subject = f"💼 {len(jobs)} ofertas LinkedIn — {now}" if jobs else f"LinkedIn Job Agent — sin novedades {now}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER

    if jobs:
        html = _build_html_email(jobs)
    else:
        html = "<p>No hay nuevas ofertas relevantes hoy.</p>"

    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        logger.info(f"Email sent to {GMAIL_USER}")
    except Exception as e:
        logger.error(f"Gmail error: {e}")
