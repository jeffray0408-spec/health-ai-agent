import streamlit as st
import os
import json
from functools import cached_property

# ADK 및 GenAI 모듈
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.genai import Client
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

# 💡 [핵심 1] 에이전트를 실행시켜줄 '러너'와 '세션(기억)' 모듈 추가
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# 1. UI 초기 설정
st.set_page_config(page_title="AI 헬스 매니저 PRO", layout="wide")
st.title("🏋️‍♂️ AI 헬스 매니저 PRO (GCP Vertex AI)")

# 2. GCP 인증 세팅
if "gcp_service_account" in st.secrets:
    gcp_credentials = dict(st.secrets["gcp_service_account"])
    with open("gcp_key.json", "w") as f:
        json.dump(gcp_credentials, f)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_key.json"

# 3. 에이전트 및 러너(Runner) 초기화
@st.cache_resource
def get_health_runner():
    class GlobalGemini(Gemini):
        @cached_property
        def api_client(self) -> Client:
            return Client(vertexai=True, location="global")

    # (이전과 동일한 하위 에이전트들)
    ________google_search_agent = LlmAgent(
        name='________google_search_agent',
        model='gemini-2.5-flash',
        description='Agent specialized in performing Google searches.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()]
    )
    
    ________url_context_agent = LlmAgent(
        name='________url_context_agent',
        description='Agent specialized in fetching content from URLs.',
        model='gemini-2.5-flash',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context]
    )
    
    agent__ = LlmAgent(
        name='agent__',
        model='gemini-2.5-flash',
        description='',
        sub_agents=[],
        instruction='',
        tools=[
            agent_tool.AgentTool(agent=________google_search_agent),
            agent_tool.AgentTool(agent=________url_context_agent)
        ]
    )
    
    ai_________google_search_agent = LlmAgent(
        name='AI_________google_search_agent',
        model=GlobalGemini(model='gemini-3.5-flash'),
        description='Agent specialized in performing Google searches.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()]
    )
    
    ai_________url_context_agent = LlmAgent(
        name='AI_________url_context_agent',
        model=GlobalGemini(model='gemini-3.5-flash'),
        description='Agent specialized in fetching content from URLs.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context]
    )

    root_agent = LlmAgent(
        name='AI________',
        model=GlobalGemini(model='gemini-3.5-flash'),
        description='너는 스포츠 의학 및 운동 생리학에 능통한 엘리트 AI 헬스 매니저야.',
        sub_agents=[agent__],
        instruction='[목표]\n사용자의 매일 운동 기록을 바탕으로 점진적 과부하와 초과회복 이론에 근거하여 다음 날의 타겟 근육과 루틴을 추천해 줘.\n\n[행동 지침]\n\n사용자가 운동 기록을 입력하면, 항상 먼저 그 노력에 대해 짧고 강렬하게 칭찬해라.\n\n대화 기록을 분석하여 최근 며칠간 자극이 덜 갔던 부위를 다음 타겟으로 설정해라.\n\n추천 근거를 생리학적 관점(예: 근육 휴식 시간, 분할법 등)에서 1~2줄로 명확하게 덧붙여라.',
        tools=[
            agent_tool.AgentTool(agent=ai_________google_search_agent),
            agent_tool.AgentTool(agent=ai_________url_context_agent)
        ]
    )
    
    # 💡 [핵심 2] 에이전트를 조종할 Runner와 세션(기억) 저장소 생성 및 결합
    sessions = InMemorySessionService()
    runner = Runner(agent=root_agent, session_service=sessions)
    
    # 에이전트 대신 Runner와 세션 서비스 자체를 반환합니다.
    return runner, sessions

# 앱이 켜질 때 한 번만 Runner를 로드합니다.
runner, sessions = get_health_runner()

# 4. 고유 세션 ID 발급 (채팅 문맥 기억용)
if "adk_session" not in st.session_state:
    # Streamlit 접속자마다 고유한 ADK 대화방(세션)을 만들어줍니다.
    st.session_state.adk_session = sessions.create_session("health_app", "user_1")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 엘리트 헬스 매니저입니다. 오늘 어떤 운동을 하셨나요?"}]

# 5. UI 반복 로직
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("운동 기록을 입력하세요 (예: 벤치프레스 5세트)"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("ADK 러너가 생리학적 데이터를 분석 중입니다..."):
            try:
                # 💡 [핵심 3] agent가 아니라 runner를 통해 세션 ID와 함께 실행합니다!
                response = runner.run(
                    session_id=st.session_state.adk_session.id, 
                    user_message=user_input
                )
                
                reply = response.text if hasattr(response, 'text') else str(response)
                
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"실행 오류: {e}")
