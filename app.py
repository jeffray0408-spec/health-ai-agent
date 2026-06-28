import streamlit as st
import time
from openai import OpenAI  # 💡 라이브러리 교체

# 1. 설정
st.set_page_config(page_title="AI 헬스 매니저", layout="wide")
st.title("🏋️‍♂️ AI 헬스 매니저 (ChatGPT 기반)")

# OpenAI 클라이언트 설정
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("Secrets에서 OPENAI_API_KEY를 확인해주세요.")
    st.stop()

# 모델 선택 (비용 효율적이고 빠른 모델)
MODEL_ID = 'gpt-4o-mini'

# 2. 세션 초기화
if "history" not in st.session_state:
    st.session_state.history = []

# 3. OpenAI용 조언 함수
def get_ai_advice(user_input, history):
    history_str = "\n".join(history[-5:])
    prompt = f"""
    당신은 스포츠 의학 기반의 전문 헬스 매니저입니다.
    사용자의 과거 기록: {history_str}
    사용자의 오늘 운동: {user_input}
    
    답변 형식: 3줄 내외로 피드백, 다음 루틴, 근거를 제시해주세요.
    """
    try:
        # 💡 OpenAI 호출 문법
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"죄송합니다, 잠시 오류가 발생했습니다: {e}"

# 4. 화면 UI
col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.chat_input("오늘의 운동을 입력하세요!")
    if user_input:
        st.session_state.history.append(user_input)
        with st.chat_message("user"): st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("AI 분석 중..."):
                advice = get_ai_advice(user_input, st.session_state.history)
                st.markdown(advice)

with col2:
    st.subheader("📋 과거 기록")
    for item in reversed(st.session_state.history):
        st.write(f"✅ {item}")
