"""
NewsHub Agent — LangGraph 그래프 정의

아키텍처:
                           ┌──────────────────────────────────────────┐
  user_input ──→ [intake] ──→ [subscription_loader]                    │
                                        │ (Conditional Edge)           │
                   ┌────────────────────┼───────────────┐              │
             intent=youtube    intent=both       intent=news    intent=newsletter
                   │                   │               │              │
                   ↓           [both_collector]        ↓              │
           [youtube_collector]   (Send API)    [news_searcher]         │
                   │           ↙         ↘           │              │
                   │   [youtube_collector] [news_searcher]            │
                   │         (parallel)                │              │
                   └──────────────┬────────────────────┘              │
                                  ↓                                    │
                             [curator] ◀─────────────────────────────-┘
                                  ↓
                       [newsletter_writer]
                                  ↓
                                 END

★ Conditional Edge : subscription_loader → route_by_intent → 4가지 분기
★ Send API 병렬 실행: intent=both → both_collector → youtube+news 동시 수집
★ 4가지 Tool: rss_feed_tool, youtube_rss_tool, web_search_tool, load_subscriptions_tool
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from state import NewsHubState
from nodes.intake import intake_node, route_by_intent
from nodes.subscription_loader import subscription_loader_node
from nodes.youtube_collector import youtube_collector_node
from nodes.news_searcher import news_searcher_node
from nodes.trend_detector import trend_detector_node
from nodes.curator import curator_node
from nodes.newsletter_writer import newsletter_writer_node
from nodes.delivery import delivery_node
from nodes.evaluator import evaluator_node, route_after_evaluation


def build_graph() -> StateGraph:
    """NewsHub LangGraph 그래프를 조립하고 컴파일한다."""

    graph = StateGraph(NewsHubState)

    # ── 노드 등록 ──────────────────────────────────────────────
    graph.add_node("intake",               intake_node)
    graph.add_node("subscription_loader",  subscription_loader_node)
    graph.add_node("youtube_collector",    youtube_collector_node)
    graph.add_node("news_searcher",        news_searcher_node)
    graph.add_node("trend_detector",       trend_detector_node)
    graph.add_node("curator",              curator_node)
    graph.add_node("newsletter_writer",    newsletter_writer_node)
    graph.add_node("evaluator",            evaluator_node)
    graph.add_node("delivery",             delivery_node)

    # ── 진입점 ────────────────────────────────────────────────
    graph.set_entry_point("intake")

    # ── 고정 엣지 ─────────────────────────────────────────────
    graph.add_edge("intake",              "subscription_loader")

    # 수집 노드 → trend_detector (collector 결과 모두 trend_detector로 집결)
    graph.add_edge("youtube_collector",   "trend_detector")
    graph.add_edge("news_searcher",       "trend_detector")

    # trend_detector → curator → newsletter_writer
    graph.add_edge("trend_detector",      "curator")
    graph.add_edge("curator",             "newsletter_writer")
    graph.add_edge("newsletter_writer",   "evaluator")

    # ── ★ Evaluation Loop (Harness) ──────────────────────────
    # evaluator 이후 결과에 따라 delivery로 가거나 다시 writer로 돌아감
    graph.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "newsletter_writer": "newsletter_writer",
            "delivery":          "delivery",
        },
    )

    graph.add_edge("delivery",            END)

    # ── ★ Conditional Edge ────────────────────────────────────
    # subscription_loader 이후 intent 기반 분기
    #
    #  route_by_intent 반환값:
    #   "youtube_collector" → YouTube만 수집
    #   "news_searcher"     → 뉴스만 수집
    #   "both_collector"    → Send API로 병렬 수집
    #   "curator"           → 수집 건너뜀 (newsletter intent)
    graph.add_conditional_edges(
        "subscription_loader",
        route_by_intent,
        {
            "youtube_collector": "youtube_collector",
            "news_searcher":     "news_searcher",
            "curator":           "curator",
        },
    )

    return graph.compile()


# 모듈 임포트 시 그래프 인스턴스 생성
app = build_graph()
