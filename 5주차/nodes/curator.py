"""
노드 4 — Curator (큐레이션 에이전트)

수집된 YouTube 영상 + 뉴스 기사를 분석하여:
- 관련도 점수(score) 매기기
- 상위 기사 선별
- 전체 트렌드 요약 작성
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from state import NewsHubState
from llm_factory import get_llm


def curator_node(state: NewsHubState) -> dict:
    """수집된 기사들을 분석하고 큐레이션한다."""

    youtube_articles = state.get("youtube_articles", [])
    news_articles = state.get("news_articles", [])
    topics = state.get("topics", ["AI"])

    # 모든 기사 합치기
    all_articles = youtube_articles + news_articles

    if not all_articles:
        return {
            "curated_articles": [],
            "trend_summary": "수집된 기사가 없습니다. 토픽이나 소스를 확인해주세요.",
            "error_messages": ["큐레이션할 기사가 0건"],
        }

    # LLM으로 큐레이션
    llm = get_llm(temperature=0.3)

    # 기사 목록을 텍스트로 변환
    articles_text = ""
    for i, article in enumerate(all_articles[:30], 1):  # 최대 30개만 분석
        articles_text += f"""
[기사 {i}]
제목: {article.get('title', '제목 없음')}
소스: {article.get('source', '알 수 없음')}
요약: {article.get('summary', '요약 없음')[:200]}
URL: {article.get('url', '')}
---
"""

    system_prompt = f"""당신은 뉴스 큐레이터 전문가입니다.
아래 수집된 기사들을 분석하여 JSON으로 응답하세요.

관심 토픽: {', '.join(topics)}

응답 형식 (JSON만 반환):
{{
    "selected_indices": [1, 3, 5, ...],  // 선별된 기사 번호 (1-indexed, 최대 10개)
    "scores": {{1: 0.95, 3: 0.88, ...}},  // 각 기사의 관련도 점수 (0~1)
    "trend_summary": "전체 트렌드 요약 (3~5문장, 한국어)"
}}

선별 기준:
1. 관심 토픽과의 관련도
2. 정보의 신선함과 유용성
3. 출처의 신뢰도
4. 중복 내용 제거
"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=articles_text),
        ])

        import json
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)

        # 선별된 기사 추출
        selected_indices = result.get("selected_indices", list(range(1, min(8, len(all_articles) + 1))))
        scores = result.get("scores", {})
        trend_summary = result.get("trend_summary", "트렌드 요약을 생성하지 못했습니다.")

        curated = []
        for idx in selected_indices:
            if 1 <= idx <= len(all_articles):
                article = all_articles[idx - 1].copy()
                article["score"] = scores.get(str(idx), scores.get(idx, 0.5))
                curated.append(article)

        # 점수 순으로 정렬
        curated.sort(key=lambda x: x.get("score", 0), reverse=True)

        return {
            "curated_articles": curated,
            "trend_summary": trend_summary,
        }

    except Exception as e:
        # LLM 실패 시 전체 기사 그대로 반환
        for article in all_articles:
            article["score"] = 0.5

        return {
            "curated_articles": all_articles[:10],
            "trend_summary": f"LLM 큐레이션 실패, 전체 기사 반환. ({str(e)})",
            "error_messages": [f"큐레이션 LLM 실패: {str(e)}"],
        }
