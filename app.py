import streamlit as st
import time
from google import genai

# 1. 설정
st.set_page_config(page_title="AI 헬스 매니저", layout="wide")
st.title("🏋️‍♂️ AI 헬스 매니저")

# API Key 설정
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Secrets에서 API 키를 확인해주세요.")
    st.stop()

# 💡 여기서 가장 안정적인 기본 모델로 설정했습니다.
MODEL_ID = 'gemini-1.5-flash'

# 2. 세션 초기화
if "history" not in st.session_state:
    st.session_state.history = []

# 3. AI 조언 함수 (안정성 강화)
def get_ai_advice(user_input, history):
    history_str = "\n".join(history[-5:]) # 최근 5개 기록만 전달하여 토큰 절약
    prompt = f"""
    당신은 스포츠 의학 기반의 전문 헬스 매니저입니다.
    사용자의 과거 운동 기록: {history_str}
    사용자의 오늘 운동: {user_input}
    
    위 내용을 바탕으로 다음을 3줄 내외로 추천해주세요:
    1. 오늘 운동에 대한 피드백
    2. 내일 수행해야 할 추천 타겟 부위
    3. 추천 이유(근육 회복/생리학적 관점)
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return response.text
    except Exception as e:
        return "죄송합니다, 잠시 서버가 혼잡합니다. 10초 뒤에 다시 시도해주세요."

# 4. 화면 UI
col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.chat_input("오늘의 운동 내용을 입력하세요 (예: 벤치프레스 60kg 5세트)")
    if user_input:
        st.session_state.history.append(user_input)
        
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("AI가 데이터를 분석 중입니다..."):
                advice = get_ai_advice(user_input, st.session_state.history)
                st.markdown(advice)

with col2:
    st.subheader("📋 과거 기록")
    for item in reversed(st.session_state.history): # 최신 기록이 위로 오게
        st.write(f"✅ {item}")
