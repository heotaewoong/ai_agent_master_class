import streamlit as st
from swarm import Swarm
import os

# agents.py에서 정의한 초기 안내 데스크 에이전트를 가져옵니다.
from agents import triage_agent

# OpenAI API Key 설정 (환경변수나 여기에 직접 입력)
# os.environ["OPENAI_API_KEY"] = "sk-..." 

client = Swarm()

st.title("🍽️ 스마트 레스토랑 봇")
st.caption("Triage, Menu, Order, Reservation 에이전트가 협동하여 도와드립니다.")

# 세션 상태(기억) 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_agent" not in st.session_state:
    st.session_state.current_agent = triage_agent # 첫 시작은 항상 Triage Agent

# 이전 대화 내역을 화면에 그리기
for msg in st.session_state.messages:
    if msg["role"] in ["user", "assistant"] and msg.get("content"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 사용자 입력창
if prompt := st.chat_input("예: 2명 예약하고 싶어 / 비건 메뉴가 있나요?"):
    
    # 1. 사용자의 메시지를 화면에 표시하고 기록
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI의 답변을 처리하는 부분
    with st.chat_message("assistant"):
        with st.spinner(f"{st.session_state.current_agent.name}가 생각 중..."):
            
            # Swarm 프레임워크 실행 (현재 에이전트와 지금까지의 대화 내용 전달)
            response = client.run(
                agent=st.session_state.current_agent,
                messages=st.session_state.messages,
            )

            # 3. 핵심 요구사항: Handoff 발생 감지 및 UI 표시
            # 실행 전 에이전트와 실행 후 반환된 에이전트가 다르면 Handoff가 일어난 것입니다.
            if response.agent.name != st.session_state.current_agent.name:
                handoff_msg = f"🔄 **[{st.session_state.current_agent.name}]**에서 **[{response.agent.name}]**(으)로 연결합니다..."
                st.info(handoff_msg) # UI에 눈에 띄게 표시
                
                # 담당자 교체
                st.session_state.current_agent = response.agent

            # 4. 최종 답변 출력
            final_reply = response.messages[-1]["content"]
            if final_reply:
                st.markdown(final_reply)

            # 대화 기록 업데이트
            st.session_state.messages = response.messages