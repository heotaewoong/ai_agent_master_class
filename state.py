"""
NewsHub Agent — 공유 상태(State) 정의

LangGraph StateGraph에서 모든 노드가 공유하는 상태 스키마.
각 에이전트(노드)는 이 상태를 읽고, 자기 담당 필드만 업데이트한다.

아키텍처:
  intake → (conditional) → youtube_collector / news_searcher → curator → newsletter_writer
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class Article(TypedDict, total=False):
    """수집된 기사/영상 하나의 스키마"""
    title: str
    url: str
    source: str          # "youtube" | "google" | "naver" | "tavily" | RSS 소스명
    summary: str
    published: str       # ISO 날짜
    tags: list[str]      # 관련 태그
    score: float         # 큐레이터가 매긴 관련도 점수 (0~1)


class NewsHubState(TypedDict, total=False):
    """전체 파이프라인 공유 상태"""

    # ── 사용자 입력 ──
    user_input: str                              # 원본 사용자 입력
    intent: Literal[                             # intake 노드가 판별한 의도
        "youtube", "news", "both", "newsletter"
    ]
    topics: list[str]                            # 관심 토픽 키워드 목록
    youtube_channels: list[dict]                 # 유튜브 채널 목록 [{name, channel_id, tags}]

    # ── 수집 결과 ──
    youtube_articles: Annotated[list[Article], operator.add]   # YouTube에서 수집한 기사
    news_articles: Annotated[list[Article], operator.add]      # 뉴스 소스에서 수집한 기사

    # ── 큐레이션 결과 ──
    curated_articles: list[Article]              # 큐레이터가 선별·정렬한 기사
    article_clusters: list[dict]                 # 테마별 기사 클러스터 [{theme, indices, theme_summary}]
    key_insight: str                             # 핵심 인사이트 1문장
    trend_summary: str                           # 트렌드 요약

    # ── 뉴스레터 ──
    newsletter_draft: str                        # 최종 뉴스레터 초안 (마크다운)
    newsletter_format: str                       # "markdown" | "html"
    evaluation_result: str                       # "pass" | "fail"
    evaluation_feedback: str                     # 품질 평가 피드백

    # ── 구독 관리 ──
    active_rss_feeds: dict[str, str]                # 구독 로더가 필터링한 활성 RSS 피드 {name: url}

    # ── 트렌드 감지 ──
    trend_alerts: list[dict]                     # 급상승 키워드 알림 [{keyword, sources_count, total_mentions}]

    # ── 발송 결과 ──
    delivery_results: Annotated[list[str], operator.add]  # Slack/Discord/Email 발송 결과

    # ── 메타 ──
    error_messages: Annotated[list[str], operator.add]   # 에러 로그
