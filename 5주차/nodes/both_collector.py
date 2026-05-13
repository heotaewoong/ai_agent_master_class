"""
노드 2.5 — Both Collector (병렬 수집 팬아웃)

intent="both" 일 때 youtube_collector + news_searcher를
LangGraph Send API로 병렬 실행한다.

★ Send API 사용 (병렬 실행 구현)
"""

from __future__ import annotations

from langgraph.types import Send

from state import NewsHubState


def both_collector_node(state: NewsHubState) -> list[Send]:
    """
    YouTube 수집기와 뉴스 수집기를 동시에 실행한다.

    LangGraph Send API:
    - 각 Send는 독립적인 상태 복사본을 받아 병렬 실행
    - youtube_articles, news_articles는 operator.add 리듀서로 자동 병합
    - 둘 다 완료된 후 curator 노드로 자동 이동
    """
    return [
        Send("youtube_collector", dict(state)),
        Send("news_searcher", dict(state)),
    ]
