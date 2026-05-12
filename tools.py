"""
NewsHub Agent — Tools 정의

LangGraph 노드에서 사용하는 Tool 모음:
1. rss_feed_tool   — RSS 피드에서 기사 수집 (커스텀 Tool)
2. youtube_rss_tool — YouTube 채널 RSS에서 최신 영상 수집 (커스텀 Tool)
3. web_search_tool — Tavily를 이용한 웹 검색 (외부 API Tool)
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import feedparser
import httpx
from langchain_core.tools import tool


# ──────────────────────────────────────────────
# Tool 1: RSS 피드 수집 (커스텀)
# ──────────────────────────────────────────────
@tool
def rss_feed_tool(feed_url: str, max_items: int = 10, days_ago: int = 7) -> list[dict]:
    """
    RSS 피드 URL에서 최신 기사를 수집합니다.
    Google News, Naver News, TechCrunch 등 다양한 RSS 소스 지원.

    Args:
        feed_url: RSS 피드 URL
        max_items: 최대 수집 개수 (기본 10)
        days_ago: 최근 N일 이내 기사만 수집 (기본 7일, 0이면 필터 없음)

    Returns:
        기사 목록 [{title, url, summary, published, source}]
    """
    import re as _re
    from datetime import timezone, timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_ago)) if days_ago > 0 else None

    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:max_items * 3]:  # 날짜 필터 감안해 넉넉히 가져옴
            published = ""
            pub_dt = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    published = pub_dt.isoformat()
                except Exception:
                    published = getattr(entry, "published", "")

            # 날짜 필터: published가 있고 cutoff보다 오래됐으면 스킵
            if cutoff and pub_dt and pub_dt < cutoff:
                continue

            summary = getattr(entry, "summary", "")
            if summary:
                summary = _re.sub(r"<[^>]+>", "", summary).strip()[:500]

            articles.append({
                "title": getattr(entry, "title", "제목 없음"),
                "url": getattr(entry, "link", ""),
                "summary": summary,
                "published": published,
                "source": feed.feed.get("title", feed_url),
            })
            if len(articles) >= max_items:
                break
        return articles
    except Exception as e:
        return [{"error": f"RSS 수집 실패: {str(e)}"}]


# ──────────────────────────────────────────────
# Tool 2: YouTube 채널 RSS 수집 (커스텀)
# ──────────────────────────────────────────────
@tool
def youtube_rss_tool(channel_id: str, max_items: int = 5) -> list[dict]:
    """
    YouTube 채널의 RSS 피드에서 최신 영상을 수집합니다.
    YouTube 채널 ID를 받아 RSS 피드를 파싱합니다.

    Args:
        channel_id: YouTube 채널 ID (예: UCxxxxxx)
        max_items: 최대 수집 개수 (기본 5)

    Returns:
        영상 목록 [{title, url, summary, published, source}]
    """
    from datetime import timezone, timedelta

    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    days_ago = int(os.getenv("NEWS_DAYS_AGO", "7"))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_ago)) if days_ago > 0 else None

    try:
        resp = httpx.get(feed_url, timeout=10, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return [{"error": f"YouTube RSS HTTP {resp.status_code}"}]
        feed = feedparser.parse(resp.text)
        videos = []
        for entry in feed.entries[:max_items * 3]:
            published = ""
            pub_dt = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    published = pub_dt.isoformat()
                except Exception:
                    published = getattr(entry, "published", "")

            if cutoff and pub_dt and pub_dt < cutoff:
                continue

            summary = ""
            if hasattr(entry, "media_group"):
                for mg in entry.media_group:
                    if hasattr(mg, "media_description"):
                        summary = mg.media_description[0]["content"][:500]
            if not summary:
                summary = getattr(entry, "summary", "")[:500]

            videos.append({
                "title": getattr(entry, "title", "제목 없음"),
                "url": getattr(entry, "link", ""),
                "summary": summary,
                "published": published,
                "source": f"YouTube: {feed.feed.get('title', channel_id)}",
            })
            if len(videos) >= max_items:
                break
        return videos
    except Exception as e:
        return [{"error": f"YouTube RSS 수집 실패: {str(e)}"}]


# ──────────────────────────────────────────────
# Tool 2.5: YouTube 자막(Transcript) 수집
# ──────────────────────────────────────────────
@tool
def youtube_transcript_tool(video_url: str, max_chars: int = 3000) -> dict:
    """
    YouTube 영상의 자막을 가져와 텍스트로 반환합니다.
    한국어 자막 우선, 없으면 영어 자막을 사용합니다.

    Args:
        video_url: YouTube 영상 URL
        max_chars: 최대 텍스트 길이 (기본 3000자)

    Returns:
        {"video_url": url, "transcript": text, "language": lang}
    """
    import re as _re
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return {"video_url": video_url, "transcript": "", "error": "youtube-transcript-api 미설치"}

    match = _re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', video_url)
    if not match:
        return {"video_url": video_url, "transcript": "", "error": "video_id 추출 실패"}

    video_id = match.group(1)
    try:
        for lang in [["ko"], ["en"], None]:
            try:
                if lang:
                    segments = YouTubeTranscriptApi.get_transcript(video_id, languages=lang)
                else:
                    segments = YouTubeTranscriptApi.get_transcript(video_id)
                text = " ".join(s["text"] for s in segments)[:max_chars]
                return {"video_url": video_url, "transcript": text, "language": (lang or ["auto"])[0]}
            except Exception:
                continue
        return {"video_url": video_url, "transcript": "", "error": "자막 없음 (비활성화 또는 미제공)"}
    except Exception as e:
        return {"video_url": video_url, "transcript": "", "error": str(e)}


# ──────────────────────────────────────────────
# Tool 2.7: Hacker News 직접 API (무료, 키 불필요)
# ──────────────────────────────────────────────
@tool
def hacker_news_tool(topic_keywords: list[str], max_items: int = 10, min_score: int = 50) -> list[dict]:
    """
    Hacker News에서 AI/테크 상위 스토리를 수집합니다.
    완전 무료, API 키 불필요. HN 커뮤니티 점수 기반 필터링.

    Args:
        topic_keywords: 필터링할 키워드 목록
        max_items: 최대 결과 수 (기본 10)
        min_score: 최소 HN 점수 (기본 50)

    Returns:
        [{title, url, summary, published, source, hn_score}]
    """
    import json as _json
    from datetime import timezone, timedelta

    days_ago = int(os.getenv("NEWS_DAYS_AGO", "7"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
    kw_lower = [k.lower() for k in topic_keywords] + ["ai", "llm", "gpt", "agent", "model", "openai", "anthropic", "gemini"]

    try:
        # 상위 500개 스토리 ID 가져오기
        resp = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        story_ids = resp.json()[:200]

        articles = []
        for story_id in story_ids:
            if len(articles) >= max_items:
                break
            try:
                s = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5).json()
                if not s or s.get("type") != "story":
                    continue
                score = s.get("score", 0)
                if score < min_score:
                    continue
                # 날짜 필터
                pub_ts = s.get("time", 0)
                pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc) if pub_ts else None
                if pub_dt and pub_dt < cutoff:
                    continue
                title = s.get("title", "").lower()
                if not any(kw in title for kw in kw_lower):
                    continue
                published = pub_dt.isoformat() if pub_dt else ""
                articles.append({
                    "title": s.get("title", ""),
                    "url": s.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "summary": f"HN 점수: {score}점 | 댓글: {s.get('descendants', 0)}개 | 커뮤니티 토론 중",
                    "published": published,
                    "source": "Hacker News",
                })
            except Exception:
                continue
        return articles if articles else [{"error": "HN에서 관련 기사 없음 (조건 조정 필요)"}]
    except Exception as e:
        return [{"error": f"HN API 실패: {str(e)}"}]


# ──────────────────────────────────────────────
# Tool 3: Tavily 웹 검색 (외부 API)
# ──────────────────────────────────────────────
@tool
def web_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """
    웹에서 최신 뉴스를 검색합니다.
    Tavily API가 있으면 Tavily를, 없으면 DuckDuckGo(무료, API 키 불필요)로 자동 전환합니다.

    Args:
        query: 검색 쿼리 (예: "AI agent 최신 트렌드 2026")
        max_results: 최대 결과 수 (기본 5)

    Returns:
        검색 결과 [{title, url, summary, source}]
    """
    tavily_key = os.getenv("TAVILY_API_KEY", "")

    # ── 1순위: Tavily (유료/무료 티어) ──
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                include_answer=False,
            )
            results = []
            for item in response.get("results", []):
                domain = item.get("url", "").split("/")[2] if "/" in item.get("url", "") else "web"
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "summary": item.get("content", "")[:500],
                    "published": "",
                    "source": f"Tavily: {domain}",
                })
            return results
        except Exception:
            pass  # Tavily 실패 시 DuckDuckGo로 폴백

    # ── 2순위: DuckDuckGo (완전 무료, API 키 불필요) ──
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results, timelimit="m"):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "summary": item.get("body", "")[:500],
                    "published": "",
                    "source": f"DuckDuckGo: {item.get('href', '').split('/')[2] if '/' in item.get('href', '') else 'web'}",
                })
        return results if results else [{"error": "DuckDuckGo 검색 결과 없음"}]
    except Exception as e:
        return [{"error": f"웹 검색 실패 (Tavily/DDG 모두): {str(e)}"}]


# ──────────────────────────────────────────────
# Tool 4: 구독 목록 로더 (subscriptions.yaml)
# ──────────────────────────────────────────────
@tool
def load_subscriptions_tool(
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    source_type: str = "all",
) -> dict:
    """
    subscriptions.yaml에서 구독 목록을 불러옵니다.
    categories, tags, source_type으로 필터링 가능합니다.

    Args:
        categories: 필터링할 카테고리 목록 (예: ["ai", "korean"])
        tags: 필터링할 태그 목록 (예: ["AI", "LLM"])
        source_type: "youtube" | "websites" | "all" (기본값: "all")

    Returns:
        {"youtube": [...], "websites": [...]}
    """
    try:
        import yaml
    except ImportError:
        return {"error": "PyYAML이 설치되지 않았습니다. pip install pyyaml"}

    # subscriptions.yaml 위치: tools.py와 같은 디렉터리
    yaml_path = Path(__file__).parent / "subscriptions.yaml"
    if not yaml_path.exists():
        return {"error": f"subscriptions.yaml을 찾을 수 없습니다: {yaml_path}"}

    try:
        with open(yaml_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return {"error": f"YAML 파싱 실패: {str(e)}"}

    def _matches(item: dict) -> bool:
        if not item.get("enabled", True):
            return False
        if categories:
            cat_lower = [c.lower() for c in categories]
            if item.get("category", "").lower() not in cat_lower:
                return False
        if tags:
            tag_lower = [t.lower() for t in tags]
            item_tags = [t.lower() for t in item.get("tags", [])]
            if not any(t in item_tags for t in tag_lower):
                return False
        return True

    result: dict = {}

    if source_type in ("youtube", "all"):
        result["youtube"] = [ch for ch in config.get("youtube", []) if _matches(ch)]

    if source_type in ("websites", "all"):
        result["websites"] = [site for site in config.get("websites", []) if _matches(site)]

    return result


# ──────────────────────────────────────────────
# 뉴스 소스 RSS 피드 URL 목록 (하드코딩 폴백)
# ──────────────────────────────────────────────
NEWS_RSS_FEEDS = {
    # 글로벌 AI/테크 소스
    "Google AI Blog": "https://blog.google/technology/ai/rss/",
    "MIT Tech Review AI": "https://www.technologyreview.com/feed/",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "Ars Technica AI": "https://feeds.arstechnica.com/arstechnica/technology-lab",

    # 한국 소스
    "AI타임스": "https://www.aitimes.com/rss/allArticle.xml",

    # Google News (키워드 기반)
    "Google News AI": "https://news.google.com/rss/search?q=artificial+intelligence&hl=ko&gl=KR",
    "Google News 테크": "https://news.google.com/rss/search?q=technology+trends&hl=ko&gl=KR",

    # Naver News (키워드 기반 — RSS 미제공 시 Google News 한국 대체)
    "Google News AI 한국": "https://news.google.com/rss/search?q=AI+인공지능&hl=ko&gl=KR&ceid=KR:ko",
}

# 샘플 YouTube 채널 (AI/테크 관련)
SAMPLE_YOUTUBE_CHANNELS = [
    {"name": "두들리", "channel_id": "UCcbPAIfCa4q0x7x8yFXmBag", "tags": ["AI", "자동화"]},
    {"name": "노마드코더", "channel_id": "UCUpJs89fSBXNolQGOYKn0YQ", "tags": ["코딩", "AI"]},
    {"name": "조코딩", "channel_id": "UCQNE2JmbasNYbjGAcuBiRRg", "tags": ["코딩", "테크"]},
    {"name": "Fireship", "channel_id": "UCsBjURrPoezykLs9EqgamOA", "tags": ["코딩", "AI"]},
    {"name": "Matt Wolfe", "channel_id": "UCJMQphrGpmGa6bWnUKhp7rA", "tags": ["AI", "도구"]},
    {"name": "AI Explained", "channel_id": "UCNJ1Ymd5yFuUPtn21xtR6pA", "tags": ["AI", "뉴스"]},
]
