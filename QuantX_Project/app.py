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
from agents.core import quantx_agent
from agents.tools import get_available_tools_for_user

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
        available_tools = get_available_tools_for_user()
        with st.sidebar.expander("🛠️ 사용 가능한 도구"):
            for tool in available_tools:
                st.write(f"✅ {tool['description']}")
        
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
    agent_status = quantx_agent.get_agent_status()
    if agent_status["agent_initialized"]:
        st.sidebar.markdown('<div class="success-card">🤖 AI 에이전트: 정상</div>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<div class="error-card">🤖 AI 에이전트: 오류</div>', unsafe_allow_html=True)
    
    # RAG 엔진 상태
    try:
        rag_engine.initialize()
        st.sidebar.markdown('<div class="success-card">🧠 지식베이스: 정상</div>', unsafe_allow_html=True)
    except:
        st.sidebar.markdown('<div class="warning-card">🧠 지식베이스: 초기화 중</div>', unsafe_allow_html=True)
    
    # 보안 시스템 상태
    st.sidebar.markdown('<div class="success-card">🛡️ 보안 시스템: 활성</div>', unsafe_allow_html=True)

def render_main_interface():
    """
    [Main Interface] 메인 인터페이스 렌더링
    """
    user_info = auth_manager.get_user_info()
    
    if not user_info["logged_in"]:
        # 로그인하지 않은 경우
        st.warning("🔐 시스템을 사용하려면 먼저 로그인해주세요.")
        
        # 시스템 소개
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🎯 Quant-X 시스템 특징
            
            - **🤖 AI 에이전트**: smolagents CodeAgent 기반 금융 분석
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
            
            - 사내 지식베이스 검색
            - 웹 검색 및 주가 조회
            - 시장 요약 정보 제공
            - 리포트 생성 및 저장
            """)
        
        return
    
    # 로그인한 경우 메인 인터페이스 표시
    st.markdown(f"### 👋 안녕하세요, {user_info['user_id']}님!")
    
    # [Research Request] 리서치 요청 섹션
    st.markdown("### 💼 금융 리서치 요청")
    
    # 예시 질문 버튼들
    st.markdown("**💡 예시 질문:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 삼성전자 주가 분석"):
            st.session_state.example_query = "삼성전자의 최근 주가 동향과 실적을 분석해주세요."
    
    with col2:
        if st.button("🏦 시장 현황 요약"):
            st.session_state.example_query = "오늘의 주요 지수 현황과 시장 동향을 요약해주세요."
    
    with col3:
        if st.button("🔍 사내 데이터 검색"):
            st.session_state.example_query = "반도체 업종에 대한 사내 리포트를 검색해주세요."
    
    with col4:
        if st.button("📈 투자 전망 분석"):
            st.session_state.example_query = "2024년 4분기 국내 주식시장 전망을 분석해주세요."
    
    # 리서치 요청 입력
    default_query = getattr(st.session_state, 'example_query', '')
    user_request = st.text_area(
        "리서치 요청을 입력하세요:",
        value=default_query,
        height=100,
        placeholder="예: 삼성전자의 최근 실적과 주가 전망을 분석해주세요."
    )
    
    # 요청 처리 버튼
    col1, col2 = st.columns([1, 4])
    
    with col1:
        process_button = st.button("🚀 리서치 시작", type="primary", disabled=st.session_state.get('processing', False))
    
    with col2:
        if st.session_state.get('processing', False):
            st.info("🔄 처리 중입니다. 잠시만 기다려주세요...")
    
    # 요청 처리
    if process_button and user_request.strip():
        st.session_state.processing = True
        st.session_state.last_request = user_request
        
        # 진행 상태 표시
        progress_container = st.container()
        
        with progress_container:
            st.markdown("### 🔄 처리 진행 상황")
            
            # 진행 단계 표시
            with st.status("리서치 요청 처리 중...", expanded=True) as status:
                st.write("1️⃣ 보안 점검 중...")
                time.sleep(1)
                
                st.write("2️⃣ AI 에이전트 실행 중...")
                time.sleep(1)
                
                st.write("3️⃣ 사내 데이터 검색 중...")
                time.sleep(1)
                
                st.write("4️⃣ 외부 정보 수집 중...")
                time.sleep(1)
                
                st.write("5️⃣ 보고서 작성 중...")
                time.sleep(1)
                
                st.write("6️⃣ 출력 검증 중...")
                
                # 실제 에이전트 실행
                try:
                    result = quantx_agent.process_request(user_request)
                    
                    if result["success"]:
                        status.update(label="✅ 리서치 완료!", state="complete", expanded=False)
                        
                        # 결과 표시
                        st.markdown("### 📋 리서치 결과")
                        st.markdown(result["response"])
                        
                        # 메타데이터 표시
                        if "metadata" in result:
                            with st.expander("📊 처리 정보"):
                                metadata = result["metadata"]
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.metric("처리 시간", f"{datetime.now().strftime('%H:%M:%S')}")
                                
                                with col2:
                                    compliance_score = metadata.get("compliance_score", {})
                                    score = compliance_score.get("score", 0)
                                    st.metric("규제 준수 점수", f"{score}점")
                                
                                with col3:
                                    filtered = "예" if metadata.get("output_filtered", False) else "아니오"
                                    st.metric("출력 필터링", filtered)
                        
                        # 채팅 히스토리에 추가
                        st.session_state.chat_history.append({
                            "timestamp": datetime.now(),
                            "request": user_request,
                            "response": result["response"],
                            "success": True
                        })
                        
                    else:
                        status.update(label="❌ 처리 실패", state="error", expanded=True)
                        st.error(f"**오류**: {result['message']}")
                        
                        if "issues" in result:
                            st.write("**감지된 문제:**")
                            for issue in result["issues"]:
                                st.write(f"- {issue}")
                        
                        # 실패한 요청도 히스토리에 추가
                        st.session_state.chat_history.append({
                            "timestamp": datetime.now(),
                            "request": user_request,
                            "response": result.get("response", "처리 실패"),
                            "success": False,
                            "error": result.get("message", "알 수 없는 오류")
                        })
                
                except Exception as e:
                    status.update(label="💥 시스템 오류", state="error", expanded=True)
                    st.error(f"시스템 오류가 발생했습니다: {str(e)}")
        
        st.session_state.processing = False
        
        # 예시 쿼리 초기화
        if hasattr(st.session_state, 'example_query'):
            del st.session_state.example_query
    
    # [Chat History] 채팅 히스토리
    if st.session_state.chat_history:
        st.markdown("### 📚 리서치 히스토리")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):  # 최근 5개만 표시
            with st.expander(f"🕐 {chat['timestamp'].strftime('%H:%M:%S')} - {chat['request'][:50]}..."):
                st.markdown(f"**요청**: {chat['request']}")
                
                if chat['success']:
                    st.markdown("**응답**:")
                    st.markdown(chat['response'])
                else:
                    st.error(f"**오류**: {chat.get('error', '알 수 없는 오류')}")

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
        # 보안 현황
        security_report = security_guardrails.get_security_report()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**보안 시스템 상태**")
            st.info(f"상태: {security_report['guardrail_status']}")
            st.info(f"보안 레벨: {security_report['security_level']}")
            st.info(f"마지막 업데이트: {security_report['last_updated']}")
        
        with col2:
            st.markdown("**보안 규칙 현황**")
            st.metric("입력 차단 키워드", security_report["input_blacklist_size"])
            st.metric("출력 필터 규칙", security_report["output_filters_size"])
            st.metric("패턴 매칭 규칙", security_report["pattern_rules"])
        
        # 보안 권장사항
        st.markdown("**보안 권장사항**")
        for rec in security_report["recommendations"]:
            st.write(f"• {rec}")
    
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