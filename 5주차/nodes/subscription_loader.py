"""
노드 1.5 — Subscription Loader (구독 목록 로더)

intake 다음, 콘텐츠 수집 전에 실행.
subscriptions.yaml을 읽어 토픽/인텐트에 맞는 소스만 활성화한다.

★ load_subscriptions_tool 사용 (Tool 연동)
★ 사용자가 yaml을 편집하면 자동으로 반영됨
"""

from __future__ import annotations

from tools import load_subscriptions_tool, NEWS_RSS_FEEDS, SAMPLE_YOUTUBE_CHANNELS
from state import NewsHubState


# 카테고리 ↔ 토픽 키워드 매핑
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ai": ["ai", "인공지능", "llm", "gpt", "claude", "agent", "에이전트",
           "딥러닝", "머신러닝", "자동화", "automation", "chatgpt"],
    "tech": ["테크", "기술", "tech", "코딩", "개발", "programming", "software",
             "웹", "web", "앱", "app", "클라우드", "cloud"],
    "finance": ["투자", "finance", "금융", "주식", "stock", "vc", "스타트업",
                "startup", "반도체", "semiconductor", "chip"],
    "korean": ["한국", "korea", "국내", "korean"],
    "academic": ["논문", "paper", "research", "연구", "학술", "arxiv"],
    "startup": ["startup", "스타트업", "창업", "vc", "투자"],
    "general": [],  # 항상 포함
}


def subscription_loader_node(state: NewsHubState) -> dict:
    """subscriptions.yaml을 로드하고 토픽에 맞는 소스를 활성화한다."""

    topics = state.get("topics", [])
    intent = state.get("intent", "both")

    # 토픽에서 관련 카테고리 추출
    matched_categories = _resolve_categories(topics, intent)

    # ★ Tool 호출 — load_subscriptions_tool
    subs = load_subscriptions_tool.invoke({
        "categories": matched_categories if matched_categories else None,
        "tags": None,
        "source_type": "all",
    })

    if "error" in subs:
        # YAML 로드 실패 시 하드코딩 폴백
        return {
            "youtube_channels": SAMPLE_YOUTUBE_CHANNELS,
            "active_rss_feeds": NEWS_RSS_FEEDS,
            "error_messages": [f"[SubscriptionLoader] 폴백 사용: {subs['error']}"],
        }

    # YouTube 채널 목록 구성
    yt_channels = [
        {
            "name": ch["name"],
            "channel_id": ch["channel_id"],
            "tags": ch.get("tags", []),
            "category": ch.get("category", "general"),
        }
        for ch in subs.get("youtube", [])
        if ch.get("enabled", True)
    ]

    # RSS 피드 목록 구성 {name: url}
    rss_feeds: dict[str, str] = {}
    for site in subs.get("websites", []):
        if site.get("enabled", True) and site.get("url"):
            rss_feeds[site["name"]] = site["url"]

    # 활성 소스가 너무 적으면 카테고리 제한 없이 재로드
    if len(rss_feeds) < 3 or len(yt_channels) < 2:
        subs_all = load_subscriptions_tool.invoke({
            "categories": None,
            "tags": None,
            "source_type": "all",
        })
        if "error" not in subs_all:
            if len(rss_feeds) < 3:
                for site in subs_all.get("websites", []):
                    if site.get("enabled", True) and site.get("url"):
                        rss_feeds[site["name"]] = site["url"]
            if len(yt_channels) < 2:
                yt_channels = [
                    {
                        "name": ch["name"],
                        "channel_id": ch["channel_id"],
                        "tags": ch.get("tags", []),
                        "category": ch.get("category", "general"),
                    }
                    for ch in subs_all.get("youtube", [])
                    if ch.get("enabled", True)
                ]

    # 최종 폴백: 하드코딩 소스 사용
    if not rss_feeds:
        rss_feeds = NEWS_RSS_FEEDS
    if not yt_channels:
        yt_channels = SAMPLE_YOUTUBE_CHANNELS

    return {
        "youtube_channels": yt_channels,
        "active_rss_feeds": rss_feeds,
    }


def _resolve_categories(topics: list[str], intent: str) -> list[str]:
    """토픽 키워드와 인텐트를 바탕으로 관련 카테고리를 반환한다."""
    topic_lower = [t.lower() for t in topics]
    matched: set[str] = set()

    for category, keywords in _CATEGORY_KEYWORDS.items():
        if category == "general":
            continue
        for kw in keywords:
            if any(kw in topic for topic in topic_lower):
                matched.add(category)
                break

    # 아무것도 매칭 안 되면 ai + korean 기본값
    if not matched:
        matched = {"ai", "korean"}

    # korean은 intent 무관하게 항상 포함 (한국어 소스는 기본 포함)
    matched.add("korean")

    return list(matched)
