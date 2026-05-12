"""
노드 3.5 — Trend Detector (트렌드 급상승 감지)

수집된 모든 기사에서 키워드 빈도를 분석하여
여러 소스에서 동시에 급상승하는 토픽을 감지한다.
"""

from __future__ import annotations

import re
from collections import defaultdict

from state import NewsHubState

_STOP_WORDS = {
    # 영어 일반
    "the", "and", "that", "this", "with", "for", "from", "are", "was", "has",
    "have", "will", "can", "its", "new", "all", "but", "not", "more", "also",
    "ago", "day", "days", "week", "year", "time", "way", "one", "two", "three",
    "out", "get", "use", "see", "how", "now", "via", "per", "our", "your",
    # URL/기술 잡음
    "https", "http", "www", "com", "youtube", "watch", "html", "rss", "feed",
    # 한국어 일반
    "있습니다", "합니다", "있는", "하는", "으로", "에서", "이다", "한다", "된다",
    "기술", "최신", "뉴스", "기사", "관련", "통해", "대한", "위한", "라는", "이번",
    "지난", "오는", "다양", "전체", "주요", "새로운", "사용", "이후", "이전",
    "있어", "하고", "되어", "까지", "부터", "통한", "대해", "위해", "에서의",
}


def trend_detector_node(state: NewsHubState) -> dict:
    """수집된 기사에서 급상승 트렌드 키워드를 감지한다."""

    all_articles = state.get("youtube_articles", []) + state.get("news_articles", [])

    if len(all_articles) < 3:
        return {"trend_alerts": []}

    # 키워드 → 등장한 소스 집합, 등장 횟수
    keyword_sources: dict[str, set] = defaultdict(set)
    keyword_count: dict[str, int] = defaultdict(int)

    for article in all_articles:
        text = (article.get("title", "") + " " + article.get("summary", "")).strip()
        source = article.get("source", "unknown")

        # 한국어 + 영어 단어 추출 (3글자 이상)
        words = re.findall(r'[a-zA-Z]{3,}|[가-힣]{2,}', text)

        for word in words:
            w = word.lower()
            if w in _STOP_WORDS or len(w) < 2:
                continue
            keyword_sources[w].add(source)
            keyword_count[w] += 1

    # 3개 이상 다른 소스에서 언급된 키워드만 선별
    alerts = []
    for keyword, sources in keyword_sources.items():
        if len(sources) >= 2 and keyword_count[keyword] >= 3:
            alerts.append({
                "keyword": keyword,
                "sources_count": len(sources),
                "total_mentions": keyword_count[keyword],
                "sources": sorted(sources)[:5],
            })

    # 소스 수 → 언급 횟수 순 정렬
    alerts.sort(key=lambda x: (x["sources_count"], x["total_mentions"]), reverse=True)

    # 사용자 입력 토픽과 겹치는 키워드 우선 배치
    topics = [t.lower() for t in state.get("topics", [])]
    if topics:
        topic_alerts = [a for a in alerts if any(t in a["keyword"] or a["keyword"] in t for t in topics)]
        other_alerts = [a for a in alerts if a not in topic_alerts]
        alerts = topic_alerts + other_alerts

    return {"trend_alerts": alerts[:15]}
