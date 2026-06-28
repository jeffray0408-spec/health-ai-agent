import streamlit as st 
import time
from google import genai

# 1. 설정
st.set_page_config(page_title="AI 헬스 매니저", layout="wide")
st.title("🏋️‍♂️ AI 헬스 매니저")

# API Key는 Streamlit Secrets 사용
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("API 키를 확인하세요.")
    st.stop()

MODEL_ID = 'gemini-2.0-flash'

# 2. 세션 초기화
if "history" not in st.session_state:
    st.session_state.history = []

# 3. AI 분석 함수 (강력한 예외 처리)
def get_ai_advice(user_input, history):
    history_str = "\n".join(history)
    prompt = f"""
    당신은 스포츠 의학 기반 헬스 매니저입니다.
    과거 기록: {history_str}
    오늘 운동: {user_input}
    
    분석 및 다음 루틴 추천을 3줄 내외로 아주 친절하게 답변해주세요.
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return response.text
    except Exception as e:
        return f"분석 중 오류 발생: {e}"

# 4. 화면 UI
col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.chat_input("오늘의 운동을 입력하세요!")
    if user_input:
        st.session_state.history.append(user_input)
        
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("AI 분석 중..."):
                advice = get_ai_advice(user_input, st.session_state.history)
                st.markdown(advice)

with col2:
    st.subheader("📋 과거 기록")
    for item in st.session_state.history:
        st.write(f"✅ {item}")
