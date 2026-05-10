"""
노드 1 — Intake (사용자 의도 분석)

사용자 입력을 분석하여:
- 의도(intent) 판별: youtube / news / both / newsletter
- 관심 토픽(topics) 추출
- YouTube 채널 정보 설정

★ Conditional Edge의 분기 기준이 되는 핵심 노드
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from state import NewsHubState
from llm_factory import get_llm


def intake_node(state: NewsHubState) -> dict:
    """사용자 입력을 분석하여 의도와 토픽을 추출한다."""

    user_input = state.get("user_input", "")

    if not user_input:
        return {
            "intent": "both",
            "topics": ["AI", "인공지능", "자동화"],
            "error_messages": ["사용자 입력이 비어있어 기본값(both) 사용"],
        }

    # LLM을 사용해 의도와 토픽 분석
    llm = get_llm(temperature=0)

    system_prompt = """당신은 사용자 의도를 분석하는 전문가입니다.
사용자 입력을 분석하여 아래 JSON 형식으로 응답하세요. JSON만 반환하세요.

{
    "intent": "youtube" | "news" | "both" | "newsletter",
    "topics": ["토픽1", "토픽2", ...]
}

의도 판별 기준:
- "youtube": 유튜브 구독/채널/영상 관련 요청
- "news": 뉴스/기사/소식 검색 요청
- "both": 유튜브 + 뉴스 모두 수집 요청 (기본값, 명확하지 않을 때)
- "newsletter": 뉴스레터/블로그 작성 요청 (이미 수집된 기사가 있는 경우)

토픽은 사용자가 관심있어하는 주제 키워드를 한국어/영어로 추출하세요.
"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"사용자 입력: {user_input}")
        ])

        import json
        # JSON 파싱 시도
        content = response.content.strip()
        # 코드 블록 제거
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)

        intent = result.get("intent", "both")
        topics = result.get("topics", ["AI"])

        # 유효한 intent인지 확인
        if intent not in ("youtube", "news", "both", "newsletter"):
            intent = "both"

        return {
            "intent": intent,
            "topics": topics,
        }

    except Exception as e:
        # LLM 실패 시 키워드 기반 폴백
        user_lower = user_input.lower()
        if "유튜브" in user_lower or "youtube" in user_lower:
            intent = "youtube"
        elif "뉴스레터" in user_lower or "newsletter" in user_lower:
            intent = "newsletter"
        elif "뉴스" in user_lower or "news" in user_lower:
            intent = "news"
        else:
            intent = "both"

        return {
            "intent": intent,
            "topics": ["AI", "인공지능"],
            "error_messages": [f"LLM 분석 실패, 키워드 폴백: {str(e)}"],
        }


def route_by_intent(state: NewsHubState) -> list[str] | str:
    """
    ★ Conditional Edge — 의도에 따라 다음 노드를 결정한다.

    - "youtube"    → youtube_collector 만 실행
    - "news"       → news_searcher 만 실행
    - "both"       → [youtube_collector, news_searcher] 병렬 실행 (fan-out)
    - "newsletter" → curator로 바로 이동 (이미 기사가 있다고 가정)
    """
    intent = state.get("intent", "both")

    if intent == "youtube":
        return "youtube_collector"
    elif intent == "news":
        return "news_searcher"
    elif intent == "newsletter":
        return "curator"
    else:  # "both" → both_collector (Send API로 병렬 팬아웃)
        return "both_collector"
