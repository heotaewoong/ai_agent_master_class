"""
NewsHub Agent — 공유 상태(State) 정의

LangGraph StateGraph에서 모든 노드가 공유하는 상태 스키마.
각 에이전트(노드)는 이 상태를 읽고, 자기 담당 필드만 업데이트한다.

아키텍처:
  intake → (conditional) → youtube_collector / news_searcher → curator → newsletter_writer → evaluator → delivery
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


class QuizQuestion(TypedDict, total=False):
    """학습 퀴즈 문제 하나의 스키마"""
    question: str                # 질문 내용
    options: list[str]           # ["A. 선택지1", "B. 선택지2", "C. 선택지3", "D. 선택지4"]
    correct: str                 # 정답 ("A" | "B" | "C" | "D")
    explanation: str             # 정답 해설


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

    # ── 트렌드 감지 ──
    trend_alerts: list[dict]                     # 급상승 키워드 [{keyword, sources_count, total_mentions, sources}]

    # ── 큐레이션 결과 ──
    curated_articles: list[Article]              # 큐레이터가 선별·정렬한 기사
    article_clusters: list[dict]                 # 테마 클러스터 [{theme, indices, theme_summary}]
    key_insight: str                             # 핵심 인사이트 한 줄
    trend_summary: str                           # 트렌드 요약

    # ── 뉴스레터 ──
    newsletter_draft: str                        # 최종 뉴스레터 초안 (마크다운)
    newsletter_format: str                       # "markdown" | "html"

    # ── 품질 평가 ──
    evaluation_result: str                       # "pass" | "fail"
    evaluation_feedback: str                     # fail 시 개선 제안

    # ── 학습 퀴즈 ──
    quiz_questions: list[QuizQuestion]           # 뉴스레터 기반 퀴즈 문제 목록

    # ── 구독 관리 ──
    active_rss_feeds: dict[str, str]             # 구독 로더가 필터링한 활성 RSS 피드 {name: url}

    # ── 메타 ──
    error_messages: Annotated[list[str], operator.add]   # 에러 로그
