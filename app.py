import streamlit as st
import json
import time
from google import genai
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

st.set_page_config(page_title="AI 헬스 매니저", page_icon="📋", layout="wide")
st.title("🏋️‍♂️ AI 맞춤형 헬스 트레이너")

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Secrets 설정에서 GEMINI_API_KEY를 확인하세요.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = 'gemini-2.0-flash'

# 세션 상태 초기화
if "workout_history" not in st.session_state:
    st.session_state.workout_history = []
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "오늘의 운동 기록을 알려주세요!"}]

class WorkoutState(TypedDict):
    user_message: str
    history: str
    target_muscle: str
    current_status: str
    recommendation: str

def analyze_input_node(state: WorkoutState) -> Dict[str, Any]:
    # JSON 형식을 확실히 보장하기 위해 프롬프트 수정
    prompt = f"""
    당신은 운동 분석 AI입니다. 사용자의 기록을 분석해 근육군을 분류하세요.
    사용자 기록: "{state['user_message']}"
    
    규칙: 반드시 아래 JSON 형식만 반환하세요.
    {{"target_muscle": "가슴/어깨/삼두(밀기)"}}
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return {"target_muscle": json.loads(text).get("target_muscle", "기타")}
    except:
        return {"target_muscle": "기타"}

def management_node(state: WorkoutState) -> Dict[str, Any]:
    time.sleep(2)
    prompt = f"사용자가 '{state['user_message']}'를 했음. {state['history']} 기록 참고해서 다음 루틴을 친절하게 3줄 요약해줘."
    
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return {
            "current_status": f"타겟: {state['target_muscle']}",
            "recommendation": response.text.strip()
        }
    except Exception as e:
        return {"current_status": "분석 오류", "recommendation": "잠시 후 다시 시도해주세요."}

# 그래프 조립
workflow = StateGraph(WorkoutState)
workflow.add_node("analyze", analyze_input_node)
workflow.add_node("manage", management_node)
workflow.set_entry_point("analyze")
workflow.add_edge("analyze", "manage")
workflow.add_edge("manage", END)
app = workflow.compile()

# UI 구성
col1, col2 = st.columns([2, 1])
with col1:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("운동 기록을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"): st.markdown(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("계산 중..."):
                res = app.invoke({"user_message": user_input, "history": "\n".join(st.session_state.workout_history)})
                st.markdown(f"**[{res['current_status']}]**\n{res['recommendation']}")
                st.session_state.messages.append({"role": "assistant", "content": res['recommendation']})
                st.session_state.workout_history.append(user_input)
                st.rerun()

with col2:
    st.subheader("📋 기록")
    for r in st.session_state.workout_history: st.write(f"✅ {r}")
