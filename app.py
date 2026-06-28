import streamlit as st
import pandas as pd
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection

# 1. 설정
st.set_page_config(page_title="AI 헬스 매니저", layout="wide")
st.title("🏋️‍♂️ AI 헬스 매니저 (구글 시트 연동판)")

# 2. 구글 시트 및 Groq 클라이언트 설정
try:
    # 구글 시트 연결
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Groq API 연결
    client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"],
        base_url="https://api.groq.com/openai/v1"
    )
except Exception as e:
    st.error(f"설정 오류가 발생했습니다. Secrets 설정을 확인해주세요: {e}")
    st.stop()

MODEL_ID = 'llama-3.3-70b-versatile'

# 3. 데이터 불러오기 (초기화)
# 구글 시트의 'Sheet1'에서 데이터를 읽어옵니다. (ttl=0은 캐시 없이 항상 최신 데이터를 읽겠다는 뜻입니다)
if "history" not in st.session_state:
    try:
        existing_data = conn.read(worksheet="Sheet1", usecols=[0], ttl=0)
        existing_data = existing_data.dropna(how="all") # 빈 줄 제거
        st.session_state.history = existing_data.iloc[:, 0].tolist() # 리스트로 변환
    except Exception:
        # 시트가 비어있거나 아직 생성되지 않았을 경우 빈 리스트로 시작
        st.session_state.history = []

# 4. AI 조언 함수
def get_ai_advice(user_input, history):
    # 에러 방지를 위해 history의 모든 요소를 문자열로 변환하여 조인
    history_str = "\n".join([str(x) for x in history[-5:]])
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
        # 1) 화면(세션)에 데이터 추가
        st.session_state.history.append(user_input)
        
        # 2) 구글 시트에 데이터 덮어쓰기 저장 (핵심 로직!)
        new_df = pd.DataFrame({"Workout_History": st.session_state.history})
        conn.update(worksheet="Sheet1", data=new_df)
        
        with st.chat_message("user"): 
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("AI 분석 및 클라우드 저장 중..."):
                advice = get_ai_advice(user_input, st.session_state.history)
                st.markdown(advice)

with col2:
    st.subheader("📋 누적 과거 기록")
    for item in reversed(st.session_state.history):
        st.write(f"✅ {item}")
