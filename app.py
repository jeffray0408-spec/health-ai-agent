import streamlit as st
import json
from google import genai
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

# ==========================================
# ⚙️ 0. 페이지 및 API 설정
# ==========================================
st.set_page_config(page_title="AI 헬스 트레이너", page_icon="🏋️‍♂️")
st.title("🏋️‍♂️ AI 맞춤형 헬스 트레이너")

# 🚨 Streamlit Cloud의 비밀 금고(Secrets)에서 API 키를 가져옵니다.
# (코드가 깃허브에 공개되어도 API 키는 안전하게 보호됩니다!)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("서버 설정에 API 키가 등록되지 않았습니다.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = 'gemini-2.5-flash'

# ==========================================
# 1~4. LangGraph 에이전트 구조 (기존과 완전히 동일)
# ==========================================
class WorkoutState(TypedDict):
    user_message: str      
    has_pain: bool         
    rpe_score: int         
    current_status: str    
    recommendation: str    

def analyze_input_node(state: WorkoutState) -> Dict[str, Any]:
    prompt = f"""
    당신은 전문 스포츠 의학 트레이너입니다. 다음 기록을 분석하세요.
    기록: "{state['user_message']}"
    조건:
    1. 통증(관절, 찌릿함 등) 호소 여부? (true/false)
    2. 주관적 피로도(RPE)? (1~10)
    반드시 아래 JSON 형식으로만 답변하세요.
    {{"has_pain": true, "rpe_score": 8}}
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(clean_text)
        return {"has_pain": result.get("has_pain", False), "rpe_score": result.get("rpe_score", 5)}
    except:
        return {"has_pain": False, "rpe_score": 5}

def progressive_overload_node(state: WorkoutState) -> Dict[str, Any]:
    prompt = f"사용자: '{state['user_message']}'\n활기찬 트레이너 말투로 중량/횟수를 올리라고 격려하는 3줄 메시지 작성."
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return {"current_status": "🟢 정상 성장 (과부하 가능)", "recommendation": response.text.strip()}

def deloading_node(state: WorkoutState) -> Dict[str, Any]:
    prompt = f"사용자: '{state['user_message']}'\n물리치료사 말투로 무게를 낮추고 스트레칭을 권장하는 3줄 메시지 작성."
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return {"current_status": "🔴 피로/통증 감지 (회복 우선)", "recommendation": response.text.strip()}

def route_by_condition(state: WorkoutState) -> str:
    if state["has_pain"] or state["rpe_score"] >= 8:
        return "go_to_deload"
    return "go_to_overload"

workflow = StateGraph(WorkoutState)
workflow.add_node("analyze_input", analyze_input_node)
workflow.add_node("progressive_overload", progressive_overload_node)
workflow.add_node("deloading", deloading_node)
workflow.set_entry_point("analyze_input")
workflow.add_conditional_edges("analyze_input", route_by_condition, {"go_to_overload": "progressive_overload", "go_to_deload": "deloading"})
workflow.add_edge("progressive_overload", END)
workflow.add_edge("deloading", END)
app = workflow.compile()

# ==========================================
# 5. Streamlit 웹 화면 UI 로직
# ==========================================
# 대화 기록을 저장하는 메모리
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요! 오늘의 운동 기록이나 피로도를 자유롭게 입력해주세요."})

# 이전 대화들을 화면에 쭉 그려줍니다
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자가 채팅창에 글을 입력했을 때 작동하는 로직
if user_input := st.chat_input("오늘 스쿼트 100kg 했는데 무릎이..."):
    # 사용자의 말을 화면에 표시하고 기록
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # AI의 답변 대기 및 실행
    with st.chat_message("assistant"):
        with st.spinner("AI가 근육의 비명 소리를 분석 중입니다..."):
            current_input = {
                "user_message": user_input,
                "has_pain": False, "rpe_score": 0, "current_status": "", "recommendation": ""
            }
            # 에이전트 가동!
            result = app.invoke(current_input)
            
            # 답변 조합
            final_response = f"**[{result['current_status']}]**\n\n{result['recommendation']}"
            st.markdown(final_response)
            
    # AI 답변 기록
    st.session_state.messages.append({"role": "assistant", "content": final_response})