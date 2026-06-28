import streamlit as st
import json
import time
from google import genai
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

# ==========================================
# ⚙️ 0. 페이지 및 API 설정
# ==========================================
st.set_page_config(page_title="AI 헬스 매니저", page_icon="📋", layout="wide")
st.title("🏋️‍♂️ AI 맞춤형 헬스 트레이너")

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("서버 설정에 API 키가 등록되지 않았습니다. 관리자에게 문의하세요.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = 'gemini-2.0-flash'

# ==========================================
# 📊 세션 메모리 (운동 기록장) 초기화
# ==========================================
if "workout_history" not in st.session_state:
    st.session_state.workout_history = []
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 오늘의 운동 부위, 종목, 느낀 점을 입력해주세요. 체계적으로 매니지먼트 해드립니다."}]

# ==========================================
# 1. State(상태) 정의
# ==========================================
class WorkoutState(TypedDict):
    user_message: str      
    history: str           
    target_muscle: str     
    current_status: str    
    recommendation: str    

# ==========================================
# 2. Nodes(노드) 정의
# ==========================================
def analyze_input_node(state: WorkoutState) -> Dict[str, Any]:
    prompt = f"""
    사용자의 오늘 운동 기록: "{state['user_message']}"
    이 기록을 바탕으로 오늘 주력으로 사용한 근육군을 파악하세요.
    반드시 아래 JSON 형식으로만 답변하세요.
    {{"target_muscle": "가슴/어깨/삼두(밀기)"}} 또는 {{"target_muscle": "등/이두(당기기)"}} 또는 {{"target_muscle": "하체/코어"}}
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(clean_text)
        return {"target_muscle": result.get("target_muscle", "전신/기타")}
    except:
        return {"target_muscle": "분석 불가"}

def management_node(state: WorkoutState) -> Dict[str, Any]:
    # 💡 서버 과부하 방지를 위해 호출 전 2초 대기
    time.sleep(2)
    
    history_text = state['history']
    today_muscle = state['target_muscle']
    today_input = state['user_message']
    
    prompt = f"""
    당신은 스포츠 의학 기반 엘리트 AI 매니저입니다.
    [과거 기록] {history_text if history_text else "없음"}
    [오늘] {today_input} / 타겟: {today_muscle}
    
    지침:
    1. 오늘 운동 요약 및 칭찬
    2. 초과회복 이론에 따른 다음 운동 타겟 추천
    3. 생리학적 관점에서 2줄 이내의 전문적 근거 제시
    친절한 매니저 말투로 작성해줘.
    """
    
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    
    return {
        "current_status": f"오늘의 타겟: {today_muscle}",
        "recommendation": response.text.strip()
    }

# ==========================================
# 3~4. Graph 조립
# ==========================================
workflow = StateGraph(WorkoutState)
workflow.add_node("analyze_input", analyze_input_node)
workflow.add_node("management", management_node)

workflow.set_entry_point("analyze_input")
workflow.add_edge("analyze_input", "management")
workflow.add_edge("management", END)
app = workflow.compile()

# ==========================================
# 5. Streamlit UI
# ==========================================
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 AI 코칭 채팅")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("운동 내용을 입력하세요 (예: 벤치프레스 60kg 5세트)"):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("데이터 분석 및 다음 루틴 계산 중..."):
                history_str = "\n".join(st.session_state.workout_history)
                current_input = {
                    "user_message": user_input,
                    "history": history_str,
                    "target_muscle": "", "current_status": "", "recommendation": ""
                }
                result = app.invoke(current_input)
                
                final_response = f"**[{result['current_status']}]**\n\n{result['recommendation']}"
                st.markdown(final_response)
                
        st.session_state.messages.append({"role": "assistant", "content": final_response})
        st.session_state.workout_history.append(f"- {user_input} (타겟: {result['target_muscle']})")
        st.rerun()

with col2:
    st.subheader("📋 운동 기록 대시보드")
    if len(st.session_state.workout_history) > 0:
        for idx, record in enumerate(st.session_state.workout_history):
            st.success(f"Day {idx+1} {record}")
    else:
        st.write("기록이 없습니다.")
