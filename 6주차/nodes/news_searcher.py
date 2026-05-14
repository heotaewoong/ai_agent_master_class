"""
노드 3 — News Searcher (멀티소스 뉴스 검색)

여러 뉴스 소스에서 관심 토픽 기반으로 뉴스를 수집한다.
★ rss_feed_tool + web_search_tool 사용 (다중 Tool 연동)

수집 소스:
1. RSS 피드: Google News, TechCrunch, The Verge, MIT Tech Review 등
2. Tavily 웹 검색: 토픽 키워드로 최신 뉴스 검색
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from state import NewsHubState
import sys
from pathlib import Path
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.append(root)

from tools import rss_feed_tool, web_search_tool, hacker_news_tool, NEWS_RSS_FEEDS


def _within_days(published: str, days: int) -> bool:
    """published 날짜가 days일 이내인지 확인한다. 파싱 실패 시 True(포함)."""
    if not published or not days:
        return True
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return dt >= cutoff
    except Exception:
        return True


def news_searcher_node(state: NewsHubState) -> dict:
    """멀티소스에서 뉴스를 수집한다."""

    topics = state.get("topics", ["AI", "인공지능"])
    days_ago = state.get("days_ago") or int(os.getenv("NEWS_DAYS_AGO", "7"))
    all_articles = []
    errors = []

    # ── 1. RSS 피드에서 수집 ──
    # subscription_loader가 설정한 피드 우선, 없으면 하드코딩 폴백
    subscription_feeds = state.get("active_rss_feeds") or {}
    feed_pool = subscription_feeds if subscription_feeds else NEWS_RSS_FEEDS
    selected_feeds = _select_relevant_feeds(topics, feed_pool)

    for feed_name, feed_url in selected_feeds.items():
        try:
            # ★ Tool 호출 — rss_feed_tool
            result = rss_feed_tool.invoke({
                "feed_url": feed_url,
                "max_items": 5,
            })

            if isinstance(result, list):
                for item in result:
                    if "error" in item:
                        errors.append(f"[RSS:{feed_name}] {item['error']}")
                        continue
                    if not _within_days(item.get("published", ""), days_ago):
                        continue
                    item["tags"] = topics
                    all_articles.append(item)
        except Exception as e:
            errors.append(f"[RSS:{feed_name}] 수집 실패: {str(e)}")

    # ── 2. Hacker News 직접 API ──
    try:
        hn_result = hacker_news_tool.invoke({
            "topic_keywords": topics,
            "max_items": 8,
            "min_score": 50,
        })
        for item in hn_result:
            if "error" not in item and _within_days(item.get("published", ""), days_ago):
                item["tags"] = topics
                all_articles.append(item)
    except Exception as e:
        errors.append(f"[HN] 수집 실패: {str(e)}")

    # ── 3. Tavily 웹 검색으로 보충 ──
    for topic in topics[:3]:  # 토픽별 최대 3개 검색
        try:
            query = f"{topic} 최신 뉴스 2026"
            # ★ Tool 호출 — web_search_tool
            result = web_search_tool.invoke({
                "query": query,
                "max_results": 3,
            })

            if isinstance(result, list):
                for item in result:
                    if "error" in item:
                        errors.append(f"[Tavily:{topic}] {item['error']}")
                        continue
                    item["tags"] = [topic]
                    all_articles.append(item)
        except Exception as e:
            errors.append(f"[Tavily:{topic}] 검색 실패: {str(e)}")

    # 중복 URL 제거
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)

    return {
        "news_articles": unique_articles,
        "error_messages": errors if errors else [],
    }


def _select_relevant_feeds(topics: list[str], feed_pool: dict[str, str]) -> dict[str, str]:
    """토픽과 관련된 RSS 피드를 선택한다. feed_pool이 subscription_loader의 결과물."""

    # subscription_loader가 이미 카테고리 필터링을 했으므로
    # 여기서는 추가로 토픽 키워드 기반 우선순위 정렬 + 최대 12개 제한만 수행

    topic_lower = [t.lower() for t in topics]

    ai_keywords = ["ai", "인공지능", "llm", "gpt", "에이전트", "agent", "자동화",
                   "automation", "딥러닝", "머신러닝", "deepmind", "openai", "anthropic"]
    tech_keywords = ["테크", "기술", "코딩", "프로그래밍", "개발", "tech", "coding",
                     "programming", "software", "ieee", "hacker", "wired"]
    korean_keywords = ["한국", "korea", "korean", "ai타임스", "전자", "블로터", "zdnet"]

    def _priority(name: str) -> int:
        name_l = name.lower()
        if any(kw in name_l for kw in korean_keywords):
            return 0  # 한국 소스 항상 최우선
        if any(
            any(kw in topic for kw in ai_keywords) for topic in topic_lower
        ) and any(kw in name_l for kw in ai_keywords + ["mit", "batch", "deeplearning", "hugging"]):
            return 1
        if any(
            any(kw in topic for kw in tech_keywords) for topic in topic_lower
        ) and any(kw in name_l for kw in tech_keywords):
            return 2
        return 3

    sorted_feeds = sorted(feed_pool.items(), key=lambda kv: _priority(kv[0]))

    # 최대 12개 (구독 피드가 많을 때 성능 조절)
    return dict(sorted_feeds[:12])
