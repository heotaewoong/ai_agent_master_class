"""
노드 6 — Delivery (자동 발송)

뉴스레터를 Slack, Discord, Email로 자동 발송한다.
환경변수에 설정된 채널만 활성화된다.

환경변수:
  SLACK_WEBHOOK_URL   — Slack Incoming Webhook URL
  DISCORD_WEBHOOK_URL — Discord Webhook URL
  EMAIL_FROM          — 발신 이메일 (Gmail 권장)
  EMAIL_PASSWORD      — Gmail 앱 비밀번호
  EMAIL_TO            — 수신 이메일 (쉼표 구분 가능)
  EMAIL_SMTP_HOST     — SMTP 호스트 (기본: smtp.gmail.com)
  EMAIL_SMTP_PORT     — SMTP 포트 (기본: 587)
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from state import NewsHubState


def delivery_node(state: NewsHubState) -> dict:
    """설정된 모든 채널로 뉴스레터를 발송한다."""

    newsletter = state.get("newsletter_draft", "")
    topics = state.get("topics", ["AI"])
    trend_alerts = state.get("trend_alerts", [])

    if not newsletter:
        return {"delivery_results": ["발송 스킵: 뉴스레터 없음"]}

    topic_str = ", ".join(topics)
    results = []

    # ── Slack ──────────────────────────────────────
    slack_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if slack_url:
        results.append(_send_slack(slack_url, newsletter, topic_str, trend_alerts))

    # ── Discord ────────────────────────────────────
    discord_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if discord_url:
        results.append(_send_discord(discord_url, newsletter, topic_str, trend_alerts))

    # ── Email ──────────────────────────────────────
    email_from = os.getenv("EMAIL_FROM", "")
    email_to = os.getenv("EMAIL_TO", "")
    if email_from and email_to:
        results.append(_send_email(newsletter, topic_str, email_from, email_to))

    if not results:
        results.append("발송 채널 미설정 (SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL / EMAIL_* 확인)")

    return {"delivery_results": results}


# ──────────────────────────────────────────────
# Slack
# ──────────────────────────────────────────────
def _send_slack(webhook_url: str, newsletter: str, topic_str: str, trend_alerts: list) -> str:
    try:
        # Slack 2000자 제한 — 앞부분만 발송
        preview = newsletter[:1800] + ("\n\n_[전체 내용은 파일 참조]_" if len(newsletter) > 1800 else "")

        trend_text = ""
        if trend_alerts:
            top = trend_alerts[:5]
            trend_text = "\n\n*🔥 급상승 키워드*\n" + "\n".join(
                f"• `{a['keyword']}` — {a['sources_count']}개 소스, {a['total_mentions']}회 언급"
                for a in top
            )

        payload = {
            "text": f"📡 *NewsHub Daily — {topic_str}*",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"📡 *NewsHub Daily — {topic_str}*{trend_text}"}},
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": preview}},
            ],
        }
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            return "✅ Slack 발송 완료"
        return f"❌ Slack 발송 실패: HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ Slack 오류: {str(e)}"


# ──────────────────────────────────────────────
# Discord
# ──────────────────────────────────────────────
def _send_discord(webhook_url: str, newsletter: str, topic_str: str, trend_alerts: list) -> str:
    try:
        # Discord 2000자 제한 — 전체 뉴스레터를 청크로 나눠 전송
        chunks = [newsletter[i:i+1900] for i in range(0, len(newsletter), 1900)]

        # 1번째 메시지: 제목 + 트렌드 알림
        trend_text = ""
        if trend_alerts:
            top = trend_alerts[:5]
            trend_text = "\n\n🔥 **급상승 키워드**\n" + "\n".join(
                f"• `{a['keyword']}` — {a['sources_count']}개 소스, {a['total_mentions']}회"
                for a in top
            )

        first_payload = {"content": f"📡 **NewsHub Daily — {topic_str}**{trend_text}"}
        resp = httpx.post(webhook_url, json=first_payload, timeout=15)
        if resp.status_code not in (200, 204):
            return f"❌ Discord 발송 실패: HTTP {resp.status_code} — {resp.text[:200]}"

        # 본문 청크 발송
        import time
        for i, chunk in enumerate(chunks):
            resp = httpx.post(webhook_url, json={"content": chunk}, timeout=15)
            if resp.status_code not in (200, 204):
                return f"❌ Discord 청크 {i+1}/{len(chunks)} 실패: HTTP {resp.status_code}"
            # Discord rate limit 방지 (0.5초 간격)
            if i < len(chunks) - 1:
                time.sleep(0.5)

        return f"✅ Discord 발송 완료 ({len(chunks)}개 메시지)"
    except Exception as e:
        return f"❌ Discord 오류: {type(e).__name__}: {str(e)}"


# ──────────────────────────────────────────────
# Email (Gmail SMTP)
# ──────────────────────────────────────────────
def _send_email(newsletter: str, topic_str: str, email_from: str, email_to_raw: str) -> str:
    try:
        password = os.getenv("EMAIL_PASSWORD", "")
        smtp_host = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        recipients = [e.strip() for e in email_to_raw.split(",") if e.strip()]

        if not password:
            return "❌ Email 오류: EMAIL_PASSWORD 미설정"

        # 마크다운 → HTML 간단 변환
        html_body = _md_to_simple_html(newsletter)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📡 NewsHub Daily — {topic_str}"
        msg["From"] = email_from
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(newsletter, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(email_from, password)
            server.sendmail(email_from, recipients, msg.as_string())

        return f"✅ Email 발송 완료 → {', '.join(recipients)}"
    except Exception as e:
        return f"❌ Email 오류: {str(e)}"


def _md_to_simple_html(md: str) -> str:
    """마크다운을 간단한 HTML로 변환한다."""
    import re
    html = md
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = html.replace('\n\n', '</p><p>').replace('\n', '<br>')
    return f"<html><body style='font-family:sans-serif;max-width:700px;margin:auto'><p>{html}</p></body></html>"
