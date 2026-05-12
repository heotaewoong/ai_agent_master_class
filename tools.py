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
def rss_feed_tool(feed_url: str, max_items: int = 10) -> list[dict]:
    """
    RSS 피드 URL에서 최신 기사를 수집합니다.
    Google News, Naver News, TechCrunch 등 다양한 RSS 소스 지원.

    Args:
        feed_url: RSS 피드 URL
        max_items: 최대 수집 개수 (기본 10)

    Returns:
        기사 목록 [{title, url, summary, published, source}]
    """
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:max_items]:
            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except Exception:
                    published = getattr(entry, "published", "")

            summary = getattr(entry, "summary", "")
            # HTML 태그 간단 제거
            if summary:
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

            articles.append({
                "title": getattr(entry, "title", "제목 없음"),
                "url": getattr(entry, "link", ""),
                "summary": summary,
                "published": published,
                "source": feed.feed.get("title", feed_url),
            })
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
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        feed = feedparser.parse(feed_url)
        videos = []
        for entry in feed.entries[:max_items]:
            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except Exception:
                    published = getattr(entry, "published", "")

            # YouTube RSS에서는 media:group > media:description에 설명이 있음
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
        return videos
    except Exception as e:
        return [{"error": f"YouTube RSS 수집 실패: {str(e)}"}]


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
