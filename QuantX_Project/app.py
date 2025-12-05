"""
[Streamlit UI] Quant-X 금융 리서치 포털

이 모듈은 금융 엔터프라이즈 AI 에이전트 시스템의 사용자 인터페이스를 구현합니다.
Streamlit을 활용하여 직관적이고 전문적인 사내 리서치 포털을 제공합니다.

교육 목표:
- Streamlit을 활용한 엔터프라이즈급 UI 구현
- 실시간 로그 모니터링 및 관리자 대시보드 구현
- 사용자 권한에 따른 동적 UI 구성
- 보안 상태 시각화 및 시스템 모니터링 구현
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json

# [Core Modules] 핵심 시스템 모듈
from core.auth import auth_manager
from core.logger import audit_logger
from core.guardrails import security_guardrails
from core.rag_engine import rag_engine
from agents.core import create_agent
# from agents.tools import get_available_tools_for_user  # 현재 사용하지 않음

# [Page Configuration] 페이지 설정
st.set_page_config(
    page_title="Quant-X | 금융 리서치 포털",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [Custom CSS] 커스텀 스타일링
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .status-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
    }
    
    .warning-card {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
    }
    
    .success-card {
        background: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    
    .error-card {
        background: #f8d7da;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
        margin: 0.5rem 0;
    }
    
    .log-entry {
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        background: #f8f9fa;
        padding: 0.5rem;
        border-radius: 4px;
        margin: 0.2rem 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """
    [Session State] 세션 상태 초기화
    
    Streamlit 세션 상태를 초기화하여 사용자 세션을 관리합니다.
    """
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.chat_history = []
        st.session_state.last_request = ""
        st.session_state.processing = False

def render_header():
    """
    [Header] 페이지 헤더 렌더링
    """
    st.markdown("""
    <div class="main-header">
        <h1>🏦 Quant-X Financial Research Portal</h1>
        <p>금융 엔터프라이즈 AI 에이전트 시스템</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """
    [Sidebar] 사이드바 렌더링
    
    로그인, 사용자 정보, 실시간 로그, 시스템 상태를 표시합니다.
    """
    st.sidebar.title("🔐 사용자 인증")
    
    # [Login Section] 로그인 섹션
    user_info = auth_manager.get_user_info()
    
    if not user_info["logged_in"]:
        # 로그인 폼
        with st.sidebar.form("login_form"):
            st.write("**사용자 ID를 입력하세요:**")
            user_id = st.text_input("User ID", placeholder="예: senior_manager, analyst_kim")
            login_button = st.form_submit_button("로그인")
            
            if login_button and user_id:
                try:
                    session = auth_manager.login(user_id)
                    st.success(f"환영합니다, {user_id}님!")
                    st.rerun()
                except Exception as e:
                    st.error(f"로그인 실패: {e}")
        
        # 로그인 가이드
        st.sidebar.info("""
        **로그인 가이드:**
        - `senior_manager`: 시니어 매니저 (모든 권한)
        - `analyst_kim`: 주니어 애널리스트 (조회만 가능)
        """)
    
    else:
        # 사용자 정보 표시
        st.sidebar.success(f"**로그인됨**: {user_info['user_id']}")
        st.sidebar.write(f"**역할**: {user_info['role_display']}")
        st.sidebar.write(f"**로그인 시간**: {user_info['login_time']}")
        
        # 권한 정보
        with st.sidebar.expander("🔑 권한 정보"):
            st.write(auth_manager.get_permission_summary())
        
        # 사용 가능한 도구
        with st.sidebar.expander("🛠️ 사용 가능한 도구"):
            st.write("✅ 사내 지식베이스 검색")
            st.write("✅ 웹 검색 및 주가 조회")
            st.write("✅ 시장 요약 정보 제공")
            if user_info["role"] == "SENIOR_MANAGER":
                st.write("✅ 리포트 생성 및 저장")
        
        # 로그아웃 버튼
        if st.sidebar.button("로그아웃"):
            auth_manager.logout()
            st.rerun()
    
    st.sidebar.divider()
    
    # [Real-time Logs] 실시간 감사 로그
    st.sidebar.title("📋 실시간 감사 로그")
    
    # 로그 새로고침 버튼
    if st.sidebar.button("🔄 로그 새로고침"):
        st.rerun()
    
    # 최근 로그 표시
    recent_logs = audit_logger.get_recent_logs(10)
    
    if recent_logs:
        for log in reversed(recent_logs[-5:]):  # 최근 5개만 표시
            timestamp = log.get('timestamp', '')[:19].replace('T', ' ')
            user_id = log.get('user_id', 'Unknown')
            action = log.get('action', 'Unknown')
            
            # 보안 이벤트는 다른 색상으로 표시
            if '🔒' in action:
                st.sidebar.markdown(f"""
                <div class="warning-card">
                    <small>{timestamp}</small><br>
                    <strong>{user_id}</strong>: {action}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f"""
                <div class="log-entry">
                    <small>{timestamp}</small><br>
                    <strong>{user_id}</strong>: {action}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.sidebar.info("로그가 없습니다.")
    
    st.sidebar.divider()
    
    # [System Status] 시스템 상태
    st.sidebar.title("⚡ 시스템 상태")
    
    # 에이전트 상태
    try:
        # 임시 에이전트 생성으로 상태 확인
        test_agent = create_agent("system_check")
        if test_agent.is_demo_mode:
            st.sidebar.markdown('<div class="warning-card">🤖 AI 에이전트: 데모 모드</div>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<div class="success-card">🤖 AI 에이전트: 정상</div>', unsafe_allow_html=True)
    except:
        st.sidebar.markdown('<div class="error-card">🤖 AI 에이전트: 오류</div>', unsafe_allow_html=True)
    
    # RAG 엔진 상태
    try:
        rag_engine.initialize()
        st.sidebar.markdown('<div class="success-card">🧠 지식베이스: 정상</div>', unsafe_allow_html=True)
    except:
        st.sidebar.markdown('<div class="warning-card">🧠 지식베이스: 초기화 중</div>', unsafe_allow_html=True)
    
    # 보안 시스템 상태 (고급 정보 포함)
    try:
        from core.guardrails import security_guardrails
        security_report = security_guardrails.get_security_report()
        
        if security_report["security_level"] == "최고":
            st.sidebar.markdown('<div class="success-card">🛡️ 보안 시스템: 최고 (AI 모더레이션 활성)</div>', unsafe_allow_html=True)
        elif security_report["security_level"] == "높음":
            st.sidebar.markdown('<div class="warning-card">🛡️ 보안 시스템: 높음 (키워드 필터링)</div>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<div class="success-card">🛡️ 보안 시스템: 활성</div>', unsafe_allow_html=True)
            
        # 보안 계층 정보 표시
        if st.sidebar.expander("🔍 보안 상세 정보"):
            st.sidebar.write(f"**보안 점수**: {security_report['security_score']}/100")
            st.sidebar.write(f"**활성 계층**: {', '.join(security_report['active_layers'])}")
            
            if security_report["system_info"]["moderation_enabled"]:
                st.sidebar.success("✅ AI 모더레이션 활성")
            else:
                st.sidebar.warning("⚠️ AI 모더레이션 비활성")
                
    except Exception as e:
        st.sidebar.markdown('<div class="error-card">🛡️ 보안 시스템: 오류</div>', unsafe_allow_html=True)

def render_main_interface():
    """
    [Main Interface] 멀티 탭 메인 인터페이스 렌더링
    """
    user_info = auth_manager.get_user_info()
    
    if not user_info["logged_in"]:
        # 로그인하지 않은 경우
        st.warning("🔐 시스템을 사용하려면 먼저 로그인해주세요.")
        
        # 시스템 소개
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🎯 Quant-X 멀티 에이전트 시스템 특징
            
            - **🤖 멀티 에이전트**: Manager-Worker 패턴 협업 구조
            - **🔍 리서치 에이전트**: 정보 수집 전문가
            - **📈 분석 에이전트**: 시장 데이터 분석가
            - **🧠 지식베이스**: HuggingFace 금융 데이터 RAG 검색
            - **🛡️ 보안 시스템**: 입출력 필터링 및 권한 관리
            - **📋 감사 로그**: 모든 활동 추적 및 기록
            """)
        
        with col2:
            st.markdown("""
            ### 🔑 사용자 역할
            
            - **시니어 매니저**: 모든 기능 사용 가능 (리포트 저장 포함)
            - **주니어 애널리스트**: 조회 기능만 사용 가능
            
            ### 🛠️ 주요 기능
            
            - 멀티 에이전트 협업 리서치
            - 실시간 협업 과정 시각화
            - 사내 지식베이스 검색
            - 웹 검색 및 주가 조회
            - 시장 요약 정보 제공
            - 리포트 생성 및 저장
            """)
        
        return
    
    # 로그인한 경우 멀티 탭 인터페이스 표시
    st.markdown(f"### 👋 안녕하세요, {user_info['user_id']}님!")
    st.markdown("**🏦 Quant-X 멀티 에이전트 금융 리서치 포털**")
    
    # [Multi-Tab Layout] 3개의 탭으로 분리
    tab1, tab2, tab3 = st.tabs(["📋 종합 상황판", "🕵️ 리서치 센터", "📈 시장 분석실"])
    
    with tab1:
        render_dashboard_tab(user_info)
    
    with tab2:
        render_research_tab(user_info)
    
    with tab3:
        render_analysis_tab(user_info)


def render_dashboard_tab(user_info):
    """
    [종합 상황판] 매니저의 요약 브리핑 및 최종 보고서 탭
    """
    st.markdown("## 📋 종합 상황판 (Dashboard)")
    st.markdown("매니저 에이전트의 종합 브리핑 및 최종 보고서를 확인할 수 있습니다.")
    
    # [리서치 요청 섹션]
    st.markdown("### 💼 금융 리서치 요청")
    
    # 예시 질문 버튼들
    st.markdown("**💡 예시 질문:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 삼성전자 주가 분석", key="dash_samsung"):
            st.session_state.example_query = "삼성전자의 최근 주가 동향과 실적을 분석해주세요."
    
    with col2:
        if st.button("🏦 시장 현황 요약", key="dash_market"):
            st.session_state.example_query = "오늘의 주요 지수 현황과 시장 동향을 요약해주세요."
    
    with col3:
        if st.button("🔍 사내 데이터 검색", key="dash_internal"):
            st.session_state.example_query = "반도체 업종에 대한 사내 리포트를 검색해주세요."
    
    with col4:
        if st.button("📈 투자 전망 분석", key="dash_forecast"):
            st.session_state.example_query = "2024년 4분기 국내 주식시장 전망을 분석해주세요."
    
    # 리서치 요청 입력
    default_query = getattr(st.session_state, 'example_query', '')
    user_request = st.text_area(
        "리서치 요청을 입력하세요:",
        value=default_query,
        height=100,
        placeholder="예: 삼성전자의 최근 실적과 주가 전망을 분석해주세요.",
        key="dashboard_request"
    )
    
    # 요청 처리 버튼
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        process_button = st.button("🚀 리서치 시작", type="primary", disabled=st.session_state.get('processing', False))
    
    with col2:
        if st.session_state.get('last_result'):
            if st.button("🔄 재분석 요청", help="이전 결과를 바탕으로 재분석을 요청합니다"):
                st.session_state.reanalysis_requested = True
    
    with col3:
        if st.session_state.get('processing', False):
            st.info("🔄 멀티 에이전트가 협업 중입니다...")
    
    # [멀티 에이전트 협업 과정 시각화]
    if st.session_state.get('processing', False) or st.session_state.get('last_collaboration_log'):
        render_collaboration_status()
    
    # 요청 처리
    if process_button and user_request.strip():
        process_multi_agent_request(user_request, user_info)
    
    # [HITL 인터페이스] Human-in-the-Loop 버튼
    if st.session_state.get('last_result') and not st.session_state.get('processing', False):
        render_hitl_interface()
    
    # [최종 보고서 표시]
    if st.session_state.get('last_result'):
        st.markdown("### 📋 최종 리서치 보고서")
        st.markdown(st.session_state.last_result)
        
        # 처리 정보 표시
        with st.expander("📊 처리 정보"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("처리 시간", st.session_state.get('last_process_time', 'N/A'))
            with col2:
                mode = "데모 모드" if st.session_state.get('is_demo_mode', True) else "AI 모드"
                st.metric("실행 모드", mode)
            with col3:
                agent_count = len(st.session_state.get('last_collaboration_log', []))
                st.metric("협업 단계", f"{agent_count}단계")


def render_research_tab(user_info):
    """
    [리서치 센터] 리서처 에이전트가 수집한 정보 표시 탭
    """
    st.markdown("## 🕵️ 리서치 센터 (Research Center)")
    st.markdown("리서치 에이전트가 수집한 뉴스, 공시 자료 및 사내 데이터를 확인할 수 있습니다.")
    
    # [멀티 에이전트 세션 상태 가져오기]
    from agents.core import get_session_state
    agent_state = get_session_state()
    
    # [리서치 결과 표시]
    research_results = agent_state.get("research_results", [])
    
    if research_results:
        st.markdown(f"### 📚 수집된 정보 ({len(research_results)}건)")
        
        for i, result in enumerate(reversed(research_results[-5:]), 1):  # 최근 5개만 표시
            with st.expander(f"🔍 리서치 #{i} - {result.get('timestamp', '')[:19]}"):
                st.markdown(f"**질의**: {result.get('query', 'N/A')}")
                st.markdown("**수집된 정보**:")
                st.markdown(result.get('findings', 'N/A'))
                
                # 메타데이터 표시
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("에이전트", result.get('agent', 'N/A'))
                with col2:
                    st.metric("정보량", f"{len(result.get('findings', ''))}자")
    else:
        st.info("🔍 아직 수집된 리서치 정보가 없습니다. 종합 상황판에서 리서치를 요청해보세요.")
    
    # [사내 데이터 검색 인터페이스]
    st.markdown("### 🏢 사내 데이터 직접 검색")
    
    search_query = st.text_input("사내 지식베이스 검색:", placeholder="예: 반도체 업종 분석")
    
    if st.button("🔍 사내 검색 실행"):
        if search_query:
            with st.spinner("사내 데이터베이스 검색 중..."):
                # 직접 사내 검색 실행
                from agents.tools import search_internal
                search_result = search_internal(search_query)
                
                st.markdown("### 🏢 사내 검색 결과")
                st.markdown(search_result)
        else:
            st.warning("검색어를 입력해주세요.")
    
    # [웹 검색 인터페이스]
    st.markdown("### 🌐 외부 정보 검색")
    
    web_query = st.text_input("웹 검색:", placeholder="예: 삼성전자 최신 뉴스")
    
    if st.button("🌐 웹 검색 실행"):
        if web_query:
            with st.spinner("웹 검색 중..."):
                # 직접 웹 검색 실행
                from agents.tools import search_web
                web_result = search_web(web_query)
                
                st.markdown("### 🌐 웹 검색 결과")
                st.markdown(web_result)
        else:
            st.warning("검색어를 입력해주세요.")


def render_analysis_tab(user_info):
    """
    [시장 분석실] 애널리스트가 분석한 주가 차트 및 재무 지표 표시 탭
    """
    st.markdown("## 📈 시장 분석실 (Market Analysis Lab)")
    st.markdown("시장 분석 에이전트가 분석한 주가 차트와 재무 지표를 확인할 수 있습니다.")
    
    # [멀티 에이전트 세션 상태 가져오기]
    from agents.core import get_session_state
    agent_state = get_session_state()
    
    # [분석 결과 표시]
    analysis_results = agent_state.get("analysis_results", [])
    intermediate_outputs = agent_state.get("intermediate_outputs", {})
    
    if analysis_results:
        st.markdown(f"### 📊 분석 보고서 ({len(analysis_results)}건)")
        
        for i, result in enumerate(reversed(analysis_results[-3:]), 1):  # 최근 3개만 표시
            with st.expander(f"📈 분석 #{i} - {result.get('timestamp', '')[:19]}"):
                st.markdown(f"**분석 대상**: {result.get('query', 'N/A')}")
                st.markdown("**분석 결과**:")
                st.markdown(result.get('analysis', 'N/A'))
    
    # [주가 차트 시각화]
    st.markdown("### 📈 주가 차트 시각화")
    
    # 저장된 주가 데이터 찾기
    stock_data_keys = [key for key in intermediate_outputs.keys() if key.startswith('stock_data_')]
    
    if stock_data_keys:
        # 가장 최근 주가 데이터 선택
        latest_stock_key = max(stock_data_keys, key=lambda x: intermediate_outputs[x].get('timestamp', ''))
        stock_data = intermediate_outputs[latest_stock_key]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 주가 차트 그리기
            if stock_data.get('dates') and stock_data.get('prices'):
                import pandas as pd
                
                chart_df = pd.DataFrame({
                    'Date': pd.to_datetime(stock_data['dates']),
                    'Price': stock_data['prices']
                })
                
                st.markdown(f"**{stock_data.get('symbol', 'N/A')} 주가 추이 (30일)**")
                st.line_chart(chart_df.set_index('Date'))
        
        with col2:
            # 주요 지표 표시
            st.markdown("**주요 지표**")
            st.metric("현재가", f"{stock_data.get('current_price', 0):,.0f}원")
            st.metric("변동", f"{stock_data.get('change', 0):+,.0f}원", 
                     f"{stock_data.get('change_percent', 0):+.2f}%")
            st.metric("거래량", f"{stock_data.get('volume', 0):,}주")
    
    # [시장 지수 차트]
    st.markdown("### 🏦 시장 지수 현황")
    
    market_summary = intermediate_outputs.get('market_summary')
    if market_summary and market_summary.get('indices'):
        indices_data = market_summary['indices']
        
        # 지수별 현재 상황 표시
        cols = st.columns(len(indices_data))
        
        for i, (name, data) in enumerate(indices_data.items()):
            with cols[i % len(cols)]:
                change_color = "normal" if data.get('change', 0) >= 0 else "inverse"
                st.metric(
                    name,
                    f"{data.get('current', 0):,.2f}",
                    f"{data.get('change_percent', 0):+.2f}%",
                    delta_color=change_color
                )
        
        # 지수 차트 그리기 (선택된 지수)
        selected_index = st.selectbox("차트로 볼 지수 선택:", list(indices_data.keys()))
        
        if selected_index and indices_data[selected_index].get('dates'):
            import pandas as pd
            
            index_data = indices_data[selected_index]
            chart_df = pd.DataFrame({
                'Date': pd.to_datetime(index_data['dates']),
                'Value': index_data['values']
            })
            
            st.markdown(f"**{selected_index} 7일 추이**")
            st.line_chart(chart_df.set_index('Date'))
    
    # [직접 주가 조회 인터페이스]
    st.markdown("### 💰 실시간 주가 조회")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        stock_symbol = st.text_input("주식 심볼 입력:", placeholder="예: 005930.KS (삼성전자)")
    
    with col2:
        if st.button("📊 주가 조회"):
            if stock_symbol:
                with st.spinner("주가 정보 조회 중..."):
                    # 직접 주가 조회 실행
                    from agents.tools import get_stock_price
                    price_result = get_stock_price(stock_symbol)
                    
                    st.markdown("### 💰 주가 정보")
                    st.markdown(price_result)
            else:
                st.warning("주식 심볼을 입력해주세요.")
    
    # [시장 현황 조회 인터페이스]
    if st.button("🏦 시장 현황 업데이트"):
        with st.spinner("시장 현황 조회 중..."):
            # 직접 시장 현황 조회 실행
            from agents.tools import get_market_summary
            market_result = get_market_summary()
            
            st.markdown("### 🏦 시장 현황")
            st.markdown(market_result)


def render_collaboration_status():
    """
    [협업 상태 시각화] 멀티 에이전트 협업 과정 실시간 표시
    """
    st.markdown("### 🤝 멀티 에이전트 협업 상태")
    
    # [멀티 에이전트 세션 상태 가져오기]
    from agents.core import get_session_state
    agent_state = get_session_state()
    collaboration_log = agent_state.get("collaboration_log", [])
    
    if collaboration_log:
        # 최근 협업 로그 표시
        recent_logs = collaboration_log[-10:]  # 최근 10개
        
        for log in recent_logs:
            timestamp = log.get('timestamp', '')[:19].replace('T', ' ')
            agent = log.get('agent', 'Unknown')
            action = log.get('action', 'Unknown')
            
            # 에이전트별 아이콘 설정
            if 'Research' in agent:
                icon = "🔍"
                color = "blue"
            elif 'Analyst' in agent:
                icon = "📈"
                color = "green"
            elif 'Manager' in agent:
                icon = "👔"
                color = "orange"
            else:
                icon = "🤖"
                color = "gray"
            
            # 협업 로그 표시
            st.markdown(f"""
            <div style="padding: 0.5rem; margin: 0.2rem 0; border-left: 3px solid {color}; background-color: #f8f9fa;">
                <small>{timestamp}</small><br>
                <strong>{icon} {agent}</strong>: {action}
            </div>
            """, unsafe_allow_html=True)
        
        # 세션 상태에 저장 (다른 탭에서도 볼 수 있도록)
        st.session_state.last_collaboration_log = collaboration_log


def render_hitl_interface():
    """
    [HITL 인터페이스] Human-in-the-Loop 승인/재작성 요청 버튼
    """
    st.markdown("### 🤝 Human-in-the-Loop 인터페이스")
    st.markdown("AI 에이전트가 작성한 보고서를 검토하고 승인하거나 재작성을 요청할 수 있습니다.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("✅ 승인", type="primary", help="현재 보고서를 승인하고 최종 확정합니다"):
            st.session_state.report_approved = True
            st.success("✅ 보고서가 승인되었습니다!")
            
            # 승인된 보고서 저장 (권한이 있는 경우)
            user_info = auth_manager.get_user_info()
            if user_info.get("role") == "SENIOR_MANAGER":
                from agents.tools import save_report
                save_result = save_report(
                    title=f"승인된 리서치 보고서 - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    content=st.session_state.get('last_result', '')
                )
                st.info(save_result)
    
    with col2:
        if st.button("🔄 재작성 요청", help="보고서의 재작성을 요청합니다"):
            st.session_state.reanalysis_requested = True
            st.warning("🔄 재작성이 요청되었습니다. 추가 지시사항을 입력해주세요.")
    
    with col3:
        if st.session_state.get('reanalysis_requested'):
            feedback = st.text_input("재작성 지시사항:", placeholder="예: 더 자세한 기술적 분석을 포함해주세요")
            
            if st.button("📝 재작성 실행") and feedback:
                # 피드백을 포함한 재분석 요청
                original_request = st.session_state.get('last_request', '')
                new_request = f"{original_request}\n\n[재작성 지시사항]: {feedback}"
                
                user_info = auth_manager.get_user_info()
                process_multi_agent_request(new_request, user_info, is_reanalysis=True)
                
                st.session_state.reanalysis_requested = False


def process_multi_agent_request(user_request, user_info, is_reanalysis=False):
    """
    [멀티 에이전트 요청 처리] 멀티 에이전트 시스템을 통한 요청 처리
    """
    st.session_state.processing = True
    st.session_state.last_request = user_request
    
    # 진행 상태 표시
    progress_container = st.container()
    
    with progress_container:
        action_type = "재분석" if is_reanalysis else "리서치"
        st.markdown(f"### 🔄 멀티 에이전트 {action_type} 진행 상황")
        
        # 진행 단계 표시
        with st.status(f"멀티 에이전트 {action_type} 처리 중...", expanded=True) as status:
            st.write("1️⃣ 보안 점검 중...")
            time.sleep(1)
            
            st.write("2️⃣ 매니저 에이전트 초기화 중...")
            time.sleep(1)
            
            st.write("3️⃣ 리서치 에이전트 작업 시작...")
            time.sleep(1)
            
            st.write("4️⃣ 시장 분석 에이전트 작업 시작...")
            time.sleep(1)
            
            st.write("5️⃣ 매니저 에이전트 결과 취합 중...")
            time.sleep(1)
            
            st.write("6️⃣ 최종 보고서 작성 중...")
            
            # 실제 멀티 에이전트 실행
            try:
                # 멀티 에이전트 시스템 생성
                user_agent = create_agent(user_info["user_id"])
                result = user_agent.process_request(user_request)
                
                status.update(label=f"✅ 멀티 에이전트 {action_type} 완료!", state="complete", expanded=False)
                
                # 결과 저장
                st.session_state.last_result = result
                st.session_state.last_process_time = datetime.now().strftime('%H:%M:%S')
                st.session_state.is_demo_mode = user_agent.is_demo_mode
                
                # 협업 로그 저장
                collaboration_log = user_agent.get_collaboration_log()
                st.session_state.last_collaboration_log = collaboration_log
                
                # 채팅 히스토리에 추가
                if not hasattr(st.session_state, 'chat_history'):
                    st.session_state.chat_history = []
                
                st.session_state.chat_history.append({
                    "timestamp": datetime.now(),
                    "request": user_request,
                    "response": result,
                    "success": True,
                    "is_reanalysis": is_reanalysis
                })
                
                st.success(f"✅ 멀티 에이전트 {action_type}가 완료되었습니다!")
                
            except Exception as e:
                status.update(label="💥 시스템 오류", state="error", expanded=True)
                st.error(f"시스템 오류가 발생했습니다: {str(e)}")
                
                # 오류 로그 저장
                if not hasattr(st.session_state, 'chat_history'):
                    st.session_state.chat_history = []
                
                st.session_state.chat_history.append({
                    "timestamp": datetime.now(),
                    "request": user_request,
                    "error": str(e),
                    "success": False,
                    "is_reanalysis": is_reanalysis
                })
    
    st.session_state.processing = False
    
    # 예시 쿼리 초기화
    if hasattr(st.session_state, 'example_query'):
        del st.session_state.example_query

def render_admin_dashboard():
    """
    [Admin Dashboard] 관리자 대시보드 (시니어 매니저용)
    """
    user_info = auth_manager.get_user_info()
    
    if not user_info["logged_in"] or user_info["role"] != "senior_manager":
        return
    
    st.markdown("---")
    st.markdown("### 🔧 관리자 대시보드")
    
    tab1, tab2, tab3 = st.tabs(["📊 시스템 통계", "🔒 보안 현황", "📋 감사 로그"])
    
    with tab1:
        # 시스템 통계
        col1, col2, col3, col4 = st.columns(4)
        
        log_stats = audit_logger.get_log_statistics()
        
        with col1:
            st.metric("총 로그 수", log_stats["total_logs"])
        
        with col2:
            st.metric("사용자 활동", log_stats["user_actions"])
        
        with col3:
            st.metric("시스템 이벤트", log_stats["system_events"])
        
        with col4:
            st.metric("보안 이벤트", log_stats["security_events"])
        
        # 사용자별 활동 통계
        if log_stats["user_statistics"]:
            st.markdown("**사용자별 활동 통계**")
            user_df = pd.DataFrame(list(log_stats["user_statistics"].items()), 
                                 columns=["사용자", "활동 수"])
            
            fig = px.bar(user_df, x="사용자", y="활동 수", 
                        title="사용자별 활동 현황")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # 고급 보안 현황
        security_report = security_guardrails.get_security_report()
        
        # 보안 점수 표시
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="보안 점수",
                value=f"{security_report['security_score']}/100",
                delta=f"{security_report['security_level']} 등급"
            )
        
        with col2:
            st.metric(
                label="활성 보안 계층",
                value=len(security_report['active_layers']),
                delta=", ".join(security_report['active_layers'])
            )
        
        with col3:
            moderation_status = "활성" if security_report["system_info"]["moderation_enabled"] else "비활성"
            st.metric(
                label="AI 모더레이션",
                value=moderation_status,
                delta="OpenAI API" if security_report["system_info"]["moderation_enabled"] else "API 키 필요"
            )
        
        st.divider()
        
        # 보안 계층별 상세 정보
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔍 키워드 필터링**")
            keyword_info = security_report["security_layers"]["keyword_filtering"]
            st.info(f"상태: {keyword_info['status']}")
            st.write(f"• 차단 키워드: {keyword_info['blacklist_size']}개")
            st.write(f"• 패턴 규칙: {keyword_info['pattern_rules']}개")
            st.write(f"• 규제 준수 규칙: {keyword_info['compliance_rules']}개")
        
        with col2:
            st.markdown("**🤖 AI 모더레이션**")
            ai_info = security_report["security_layers"]["ai_moderation"]
            
            if ai_info['status'] == "활성":
                st.success(f"상태: {ai_info['status']}")
                st.write(f"• 제공업체: {ai_info['provider']}")
                st.write(f"• 모니터링 카테고리: {ai_info['custom_thresholds']}개")
                
                # 모니터링 카테고리 표시
                if ai_info['categories_monitored']:
                    with st.expander("모니터링 카테고리"):
                        for category in ai_info['categories_monitored']:
                            st.write(f"• {category}")
            else:
                st.warning(f"상태: {ai_info['status']}")
                st.write("• OpenAI API 키를 설정하여 활성화하세요")
        
        st.divider()
        
        # 보안 권장사항
        st.markdown("**🛡️ 보안 강화 권장사항**")
        for i, rec in enumerate(security_report["recommendations"], 1):
            st.write(f"{i}. {rec}")
        
        # 시스템 정보
        with st.expander("🔧 시스템 정보"):
            st.write(f"• OpenAI 라이브러리: {'사용 가능' if security_report['system_info']['openai_available'] else '설치 필요'}")
            st.write(f"• 총 보안 규칙: {security_report['system_info']['total_rules']}개")
            st.write(f"• 마지막 업데이트: {security_report['last_updated']}")
    
    with tab3:
        # 상세 감사 로그
        st.markdown("**상세 감사 로그**")
        
        # 로그 필터
        col1, col2 = st.columns(2)
        
        with col1:
            log_type = st.selectbox("로그 타입", ["전체", "사용자 활동", "시스템 이벤트", "보안 이벤트"])
        
        with col2:
            log_count = st.slider("표시할 로그 수", 10, 100, 20)
        
        # 로그 데이터 가져오기
        if log_type == "보안 이벤트":
            logs = audit_logger.get_security_logs(log_count)
        else:
            logs = audit_logger.get_recent_logs(log_count)
        
        # 로그 테이블 표시
        if logs:
            log_df = pd.DataFrame(logs)
            st.dataframe(log_df, use_container_width=True)
        else:
            st.info("표시할 로그가 없습니다.")

def main():
    """
    [Main Function] 메인 함수
    """
    # 세션 상태 초기화
    initialize_session_state()
    
    # 헤더 렌더링
    render_header()
    
    # 사이드바 렌더링
    render_sidebar()
    
    # 메인 인터페이스 렌더링
    render_main_interface()
    
    # 관리자 대시보드 렌더링 (권한이 있는 경우)
    render_admin_dashboard()
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        🏦 Quant-X Financial Research Portal | 
        금융 엔터프라이즈 AI 에이전트 시스템 | 
        교육용 데모 버전
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()