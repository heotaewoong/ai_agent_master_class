import streamlit as st
from swarm import Swarm
import os

# ────────────────────────────────────────────
# ⚙️  API 키 설정 (Streamlit Cloud Secrets 우선, 환경변수 폴백)
# ────────────────────────────────────────────
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

from agents import triage_agent

client = Swarm()

# ────────────────────────────────────────────
# 🛡️  Input Guardrail
# ────────────────────────────────────────────
BLOCKED_KEYWORDS = [
    "씨발", "개새끼", "병신", "fuck", "shit", "bastard", "asshole",
    "ignore previous instructions", "ignore all instructions",
    "system prompt", "jailbreak", "프롬프트 무시",
]
MAX_INPUT_LENGTH = 500


def check_input_guardrail(user_input: str) -> tuple[bool, str]:
    """
    사용자 입력을 검사합니다.
    Returns: (통과 여부: bool, 오류 메시지: str)
    """
    # 길이 제한
    if len(user_input) > MAX_INPUT_LENGTH:
        return False, f"⚠️ 입력이 너무 깁니다. {MAX_INPUT_LENGTH}자 이내로 입력해 주세요. (현재 {len(user_input)}자)"

    # 금지 키워드 검사
    lower_input = user_input.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in lower_input:
            return False, "⚠️ 부적절한 표현이 감지되었습니다. 정중한 언어를 사용해 주세요. 😊"

    return True, ""


# ────────────────────────────────────────────
# 🛡️  Output Guardrail
# ────────────────────────────────────────────
SENSITIVE_PATTERNS = [
    "sk-",           # OpenAI API 키 패턴
    "system:",       # 시스템 프롬프트 노출
    "instructions:", # 지시사항 노출
]


def check_output_guardrail(ai_response: str) -> tuple[str, bool]:
    """
    AI 응답을 검사하고 정제합니다.
    Returns: (정제된 응답: str, 경고 여부: bool)
    """
    if not ai_response:
        return "죄송합니다. 응답을 생성하지 못했습니다. 다시 시도해 주세요.", True

    warned = False
    response = ai_response

    # 민감 패턴 감지 시 응답 차단
    lower_response = response.lower()
    for pattern in SENSITIVE_PATTERNS:
        if pattern.lower() in lower_response:
            response = "죄송합니다. 응답 처리 중 문제가 발생했습니다. 다시 질문해 주세요."
            warned = True
            break

    return response, warned


# ────────────────────────────────────────────
# 🎨  페이지 설정
# ────────────────────────────────────────────
st.set_page_config(
    page_title="🍽️ 미슐랭 키친 봇",
    page_icon="🍽️",
    layout="centered",
)

# CSS 커스텀 스타일
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp {
        background: linear-gradient(135deg, #1a0a00 0%, #2d1500 50%, #1a0a00 100%);
    }

    /* 타이틀 영역 */
    .restaurant-header {
        text-align: center;
        padding: 1.5rem 1rem;
        background: linear-gradient(135deg, rgba(255,180,50,0.15), rgba(255,100,0,0.1));
        border-radius: 16px;
        border: 1px solid rgba(255,180,50,0.3);
        margin-bottom: 1.5rem;
        backdrop-filter: blur(10px);
    }
    .restaurant-header h1 {
        color: #FFD700;
        font-size: 2.2rem;
        margin: 0;
        text-shadow: 0 0 20px rgba(255,215,0,0.5);
    }
    .restaurant-header p {
        color: #FFA07A;
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }

    /* 에이전트 배지 */
    .agent-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    /* 채팅 버블 스타일 보정 */
    .stChatMessage {
        border-radius: 12px !important;
    }

    /* 입력창 스타일 */
    .stChatInputContainer {
        border-top: 1px solid rgba(255,180,50,0.2) !important;
        padding-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────
# 🏷️  헤더
# ────────────────────────────────────────────
st.markdown("""
<div class="restaurant-header">
    <h1>🍽️ 미슐랭 키친</h1>
    <p>AI 레스토랑 봇 | 메뉴 · 주문 · 예약 · 불만 처리 전문</p>
</div>
""", unsafe_allow_html=True)

# 에이전트 색상 맵
AGENT_COLORS = {
    "Triage Agent":       ("#FFD700", "🎯"),
    "Menu Agent":         ("#90EE90", "🍴"),
    "Order Agent":        ("#87CEEB", "🛒"),
    "Reservation Agent":  ("#DDA0DD", "📅"),
    "Complaints Agent":   ("#FF8C69", "😤"),
}

# ────────────────────────────────────────────
# 🧠  세션 상태 초기화
# ────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_agent" not in st.session_state:
    st.session_state.current_agent = triage_agent

# 사이드바 – 현재 에이전트 상태 표시
with st.sidebar:
    st.markdown("### 🤖 현재 담당 에이전트")
    agent_name = st.session_state.current_agent.name
    color, icon = AGENT_COLORS.get(agent_name, ("#FFFFFF", "🤖"))
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.05); border-left: 4px solid {color}; '
        f'padding:0.7rem 1rem; border-radius:8px; color:{color}; font-weight:600;">'
        f'{icon} {agent_name}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### 📋 에이전트 안내")
    for name, (c, ico) in AGENT_COLORS.items():
        st.markdown(
            f'<div style="color:{c}; margin:0.3rem 0; font-size:0.85rem;">{ico} {name}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.button("🔄 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_agent = triage_agent
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="color:rgba(255,255,255,0.4); font-size:0.75rem;">'
        '🛡️ Input & Output Guardrails 활성화<br>'
        '💬 세션 내 대화 기억 유지</div>',
        unsafe_allow_html=True,
    )

# ────────────────────────────────────────────
# 💬  이전 대화 렌더링
# ────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user" and msg.get("content"):
        with st.chat_message("user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant" and msg.get("content"):
        with st.chat_message("assistant"):
            # 에이전트명 표시 (메시지에 저장된 경우)
            agent_tag = msg.get("agent_name", "")
            if agent_tag:
                c, ico = AGENT_COLORS.get(agent_tag, ("#FFFFFF", "🤖"))
                st.markdown(
                    f'<span class="agent-badge" style="background:rgba(255,255,255,0.08); '
                    f'color:{c}; border:1px solid {c};">{ico} {agent_tag}</span>',
                    unsafe_allow_html=True,
                )
            st.markdown(msg["content"])

# ────────────────────────────────────────────
# ✏️  사용자 입력
# ────────────────────────────────────────────
if prompt := st.chat_input("예: 오늘 메뉴가 뭐가 있나요? / 2명 예약하고 싶어요"):

    # ── 1. Input Guardrail ───────────────────
    passed, error_msg = check_input_guardrail(prompt)
    if not passed:
        with st.chat_message("assistant"):
            st.warning(error_msg)
        st.stop()

    # ── 2. 사용자 메시지 표시 & 기록 ────────
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ── 3. Swarm 실행 ────────────────────────
    with st.chat_message("assistant"):
        agent_name_before = st.session_state.current_agent.name

        with st.spinner(f"{agent_name_before}가 생각 중..."):
            response = client.run(
                agent=st.session_state.current_agent,
                messages=st.session_state.messages,
            )

        # ── 4. Handoff 감지 & UI 표시 ────────
        agent_name_after = response.agent.name
        if agent_name_after != agent_name_before:
            c_before, ico_before = AGENT_COLORS.get(agent_name_before, ("#fff", "🤖"))
            c_after, ico_after  = AGENT_COLORS.get(agent_name_after,  ("#fff", "🤖"))
            st.info(
                f"🔄 **{ico_before} {agent_name_before}** → **{ico_after} {agent_name_after}** 로 연결합니다..."
            )
            st.session_state.current_agent = response.agent

        # ── 5. Output Guardrail ───────────────
        raw_reply = response.messages[-1]["content"] or ""
        final_reply, was_blocked = check_output_guardrail(raw_reply)

        if was_blocked:
            st.warning("⚠️ 응답에 문제가 감지되어 일부 내용이 필터링되었습니다.")

        # ── 6. 에이전트 배지 + 응답 출력 ─────
        current_agent_name = st.session_state.current_agent.name
        c, ico = AGENT_COLORS.get(current_agent_name, ("#FFFFFF", "🤖"))
        st.markdown(
            f'<span class="agent-badge" style="background:rgba(255,255,255,0.08); '
            f'color:{c}; border:1px solid {c};">{ico} {current_agent_name}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(final_reply)

    # ── 7. 대화 기록 업데이트 ────────────────
    # Swarm이 반환한 전체 messages를 기반으로 업데이트하되,
    # 마지막 assistant 메시지에 agent_name 태그 추가
    st.session_state.messages = response.messages
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages[-1]["agent_name"] = st.session_state.current_agent.name

    # 사이드바 에이전트 상태 즉시 반영
    st.rerun()
