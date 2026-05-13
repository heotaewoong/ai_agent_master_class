import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트를 path에 추가
root_path = str(Path(__file__).parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from graph import app

st.set_page_config(
    page_title="NewsHub Chat Agent",
    page_icon="📡",
    layout="wide",
)

st.title("📡 NewsHub Chat Agent")
st.markdown("채팅 기반으로 작동하는 AI 뉴스 큐레이션 에이전트입니다.")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정 및 정보")
    provider = os.getenv("LLM_PROVIDER", "openai")
    st.info(f"현재 LLM 프로바이더: **{provider.upper()}**")
    
    st.markdown("---")
    st.markdown("#### 💡 예시 질문")
    st.markdown("- AI 최신 트렌드 요약해줘")
    st.markdown("- LLM 관련 최신 유튜브 영상 찾아줘")
    st.markdown("- 국내 AI 스타트업 소식 알려줘")
    
    if st.button("🔄 대화 초기화"):
        st.session_state.messages = []
        st.rerun()

# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! AI/테크 전문 뉴스레터 에이전트입니다. 어떤 주제의 뉴스를 모아드릴까요?\n\n*(예: AI 최신 트렌드 알려줘)*"}
    ]

# 기존 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력 처리 (기본 채팅 인터페이스)
if prompt := st.chat_input("관심 있는 주제나 질문을 입력하세요..."):
    # 사용자 메시지 화면에 출력 및 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 에이전트 응답
    with st.chat_message("assistant"):
        with st.status("🚀 LangGraph 에이전트 워크플로우 실행 중...", expanded=True) as status:
            st.write("1. 🧠 Intake: 사용자 의도 분석 중...")
            st.write("2. ⚡ 병렬 처리 (Parallelization): YouTube 및 RSS 피드 동시 수집 중...")
            
            try:
                # 초기 상태 설정 및 LangGraph 실행 (End-to-End)
                initial_state = {"user_input": prompt}
                result = app.invoke(initial_state)
                
                st.write("3. 📝 큐레이션 및 뉴스레터 작성 중...")
                
                eval_res = result.get("evaluation_result", "N/A")
                if eval_res == "pass":
                    st.write("4. ⚖️ AI-as-Judge (Evaluator): 품질 검수 통과! ✅")
                elif eval_res == "fail":
                    st.write("4. ⚖️ AI-as-Judge (Evaluator): 품질 미달 감지, 재작성(Harness) 수행! 🔄")
                
                status.update(label="✅ 에이전트 실행 완료!", state="complete", expanded=False)
                
                # 결과 추출
                newsletter = result.get("newsletter_draft", "뉴스레터 작성에 실패했습니다.")
                
                # 최종 응답 UI 구성
                response_text = f"{newsletter}"
                
                # 화면 출력 및 세션 저장
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # 메트릭 및 상세 정보 토글
                with st.expander("📊 워크플로우 실행 상세 (고급 패턴 작동 결과)"):
                    cols = st.columns(4)
                    cols[0].metric("인텐트", result.get("intent", "").upper())
                    cols[1].metric("수집된 영상", f"{len(result.get('youtube_articles', []))}건")
                    cols[2].metric("수집된 뉴스", f"{len(result.get('news_articles', []))}건")
                    cols[3].metric("AI-Judge 검수", eval_res.upper())
                    
                    st.write(f"**활성 토픽:** {', '.join(result.get('topics', []))}")
                    st.write(f"**트렌드 경고:** {len(result.get('trend_alerts', []))}건 감지")

            except Exception as e:
                error_msg = f"에이전트 실행 중 오류가 발생했습니다: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                status.update(label="❌ 오류 발생", state="error")
