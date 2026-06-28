import streamlit as st
import json
from google import genai
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

# ==========================================
# ⚙️ 0. 페이지 및 API 설정
# ==========================================
st.set_page_config(page_title="AI 헬스 매니저", page_icon="📋", layout="wide")

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("서버 설정에 API 키가 등록되지 않았습니다.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = 'gemini-2.5-flash'

# ==========================================
# 📊 세션 메모리 (운동 기록장) 초기화
# ==========================================
# 앱을 새로고침하기 전까지 사용자의 운동 기록을 누적해서 기억합니다.
if "workout_history" not in st.session_state:
    st.session_state.workout_history = []
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 오늘 진행하신 운동 부위와 종목, 느낀 점을 자유롭게 기록해주세요. 누적된 데이터를 바탕으로 다음 운동을 코칭해 드립니다."}]

# ==========================================
# 1. State(상태) 정의: 과거 기록(history) 변수 추가
# ==========================================
class WorkoutState(TypedDict):
    user_message: str      
    history: str           # 누적된 과거 운동 기록
    target_muscle: str     # 오늘 타겟한 근육 부위
    current_status: str    
    recommendation: str    

# ==========================================
# 2. Nodes(노드) 정의
# ==========================================
def analyze_input_node(state: WorkoutState) -> Dict[str, Any]:
    # 1단계: 오늘 어떤 운동을 했는지 분석하여 카테고리화
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
        muscle = result.get("target_muscle", "전신/기타")
        return {"target_muscle": muscle}
    except:
        return {"target_muscle": "분석 불가"}

def management_node(state: WorkoutState) -> Dict[str, Any]:
    # 2단계: 과거 기록 + 오늘 운동을 종합하여 '논문 기반' 다음 루틴 추천
    history_text = state['history']
    today_muscle = state['target_muscle']
    today_input = state['user_message']
    
    prompt = f"""
    당신은 NSCA(미국체력관리학회) 및 스포츠 의학 논문 기반으로 루틴을 짜주는 엘리트 AI 매니저입니다.
    
    [사용자의 과거 운동 누적 기록]
    {history_text if history_text else "아직 과거 기록이 없습니다. 오늘이 첫 기록입니다."}
    
    [오늘의 운동 내용]
    - 상세: {today_input}
    - 타겟 근육: {today_muscle}
    
    위 데이터를 모두 종합하여 다음 지침에 따라 가이드를 작성해주세요.
    1. 오늘 진행한 운동에 대한 짧은 요약 및 칭찬
    2. 초과회복 이론(근육은 48~72시간 휴식이 필요함)을 적용하여, 내일 또는 다음 운동 세션에 진행해야 할 최적의 타겟 부위 추천
    3. 추천하는 이유를 생리학적/시스템적 관점(예: 분할 훈련법)에서 1~2줄로 전문성 있게 설명
    
    친절하고 체계적인 매니저의 말투로 작성해주세요.
    """
    
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    
    return {
        "current_status": f"오늘의 타겟: {today_muscle}",
        "recommendation": response.text.strip()
    }

# ==========================================
# 3~4. Graph(그래프) 조립 (분기 없이 분석 -> 매니지먼트로 직행)
# ==========================================
workflow = StateGraph(WorkoutState)
workflow.add_node("analyze_input", analyze_input_node)
workflow.add_node("management", management_node)

workflow.set_entry_point("analyze_input")
workflow.add_edge("analyze_input", "management")
workflow.add_edge("management", END)
app = workflow.compile()

# ==========================================
# 5. Streamlit 화면 UI 
# ==========================================
# 레이아웃을 2단으로 나누어 왼쪽은 챗봇, 오른쪽은 매니지먼트 대시보드로 활용
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 AI 코칭 채팅")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("예: 오늘 가슴 위주로 벤치프레스랑 덤벨 플라이 했어."):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("AI가 운동 기록을 동기화하고 다음 루틴을 계산 중입니다..."):
                
                # 과거 기록을 하나의 텍스트로 묶어서 AI에게 전달
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
        
        # 오늘 한 운동을 '과거 기록'에 정식으로 추가
        st.session_state.workout_history.append(f"- 기록: {user_input} (분석된 타겟: {result['target_muscle']})")
        st.rerun() # 화면을 새로고침하여 우측 대시보드 업데이트

with col2:
    st.subheader("📋 내 운동 누적 대시보드")
    st.info("이곳에 입력하신 운동 기록이 누적되어, AI가 분할법을 계산하는 뼈대 데이터로 사용됩니다.")
    
    if len(st.session_state.workout_history) > 0:
        for idx, record in enumerate(st.session_state.workout_history):
            st.success(f"Day {idx+1} | {record}")
    else:
        st.write("아직 기록된 운동이 없습니다.")
