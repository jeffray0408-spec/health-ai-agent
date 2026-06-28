import streamlit as st
import os
from functools import cached_property

# ADK 및 GenAI 모듈
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.genai import Client
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

# 1. UI 초기 설정
st.set_page_config(page_title="AI 헬스 매니저 (GCP Vertex AI)", layout="wide")
st.title("🏋️‍♂️ AI 헬스 매니저 PRO")

# 2. ADK 에이전트 초기화 (한 번만 로드되도록 캐싱)
@st.cache_resource
def get_health_agent():
    # 유저가 제공한 클래스
    class GlobalGemini(Gemini):
        @cached_property
        def api_client(self) -> Client:
            return Client(vertexai=True, location="global")

    # 하위 에이전트들
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

    # 최상위 루트 에이전트
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
    return root_agent

agent = get_health_agent()

# 3. 대화 세션 상태 관리
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 헬스 매니저입니다. 오늘 어떤 운동을 하셨나요?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 사용자 입력 및 AI 응답 처리
if user_input := st.chat_input("운동 기록을 입력하세요 (예: 데드리프트 100kg)"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("에이전트가 생리학적 데이터를 분석 중입니다..."):
            try:
                # ADK 에이전트 실행 (대화 문맥 유지)
                response = agent.run(user_input)
                
                # ADK 응답 객체에서 텍스트 추출 (버전별 호환성 처리)
                reply = response.text if hasattr(response, 'text') else str(response)
                
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"실행 오류: {e}")
