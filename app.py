import streamlit as st
import time
from openai import OpenAI

# 1. 설정
st.set_page_config(page_title="AI 헬스 매니저", layout="wide")
st.title("🏋️‍♂️ AI 헬스 매니저")

# 2. 클라이언트 설정 (괄호 닫기 확인 완료)
try:
    client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"],
        base_url="https://api.groq.com/openai/v1"
    )
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

MODEL_ID = 'llama-3.3-70b-versatile'

# 3. 세션 초기화
if "history" not in st.session_state:
    st.session_state.history = []

# 4. AI 조언 함수
def get_ai_advice(user_input, history):
    history_str = "\n".join(history[-5:])
    prompt = f"과거 기록: {history_str}\n오늘 운동: {user_input}\n위 내용을 바탕으로 피드백과 다음 루틴을 3줄로 작성해줘."
    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"분석 오류: {e}"

# 5. 화면 UI
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
