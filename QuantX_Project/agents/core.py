"""
[Multi-Agent Core] Quant-X 멀티 에이전트 협업 시스템

이 모듈은 Manager-Worker 패턴을 구현하여 역할별로 분담된 에이전트들이 협업하는 구조를 제공합니다.
교육 목표인 "멀티 에이전트 협업(Multi-Agent Collaboration)"을 실습하기 위해 설계되었습니다.

아키텍처:
- ResearchAgent (Worker): 정보 수집 전문가
- MarketAnalystAgent (Worker): 시장 데이터 분석가  
- ManagerAgent (Boss): 프로젝트 매니저 및 오케스트레이터

핵심 특징:
- smolagents.Tool.from_agent를 활용한 에이전트 간 통신
- 각 에이전트별 전문화된 프롬프트와 도구 세트
- 실시간 로그를 통한 협업 과정 시각화
- 중간 산출물 저장으로 UI 연동 지원
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# [AI Framework] smolagents 프레임워크 import
try:
    from smolagents import CodeAgent, LiteLLMModel, Tool
    SMOLAGENTS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("[Multi-Agent Core] smolagents 라이브러리 로드 성공")
except ImportError:
    try:
        from smolagents import CodeAgent, ApiModel as LiteLLMModel, Tool
        SMOLAGENTS_AVAILABLE = True
        logger = logging.getLogger(__name__)
        logger.warning("[Multi-Agent Core] LiteLLMModel을 찾을 수 없어 ApiModel로 폴백")
    except ImportError:
        SMOLAGENTS_AVAILABLE = False
        logger = logging.getLogger(__name__)
        logger.warning("[Multi-Agent Core] smolagents 라이브러리를 찾을 수 없습니다. 데모 모드로만 실행됩니다.")

# [Internal Modules] 내부 모듈 import
from agents.tools import search_internal, search_web, get_stock_price, get_market_summary, save_report
from core.logger import get_logger

logger = get_logger(__name__)

# [Global Session State] 멀티 에이전트 간 데이터 공유를 위한 전역 상태
AGENT_SESSION_STATE = {
    "research_results": [],      # 리서처가 수집한 정보
    "analysis_results": [],      # 애널리스트가 분석한 데이터
    "intermediate_outputs": {},  # 중간 산출물 저장소
    "collaboration_log": []      # 협업 과정 로그
}


class ResearchAgent:
    """
    [정보 수집 전문가] Research Agent
    
    역할: 팩트 기반의 정보를 수집하는 리서처
    전문 분야: 사내 데이터 우선 검색, 웹 검색을 통한 외부 정보 수집
    사용 도구: search_internal, search_web
    
    특징:
    - 사내 데이터를 우선적으로 검색하여 신뢰성 확보
    - 외부 정보는 보완적으로만 활용
    - 수집된 정보를 구조화하여 매니저에게 전달
    """
    
    def __init__(self, user_id: str):
        """
        [리서치 에이전트 초기화]
        
        Args:
            user_id (str): 사용자 ID (권한 체크 및 감사 로그용)
        """
        self.user_id = user_id
        self.agent = None
        self.is_demo_mode = False
        
        # [OpenAI API 키 확인]
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key or openai_api_key.startswith('your_'):
            logger.warning("[Research Agent] OpenAI API 키가 설정되지 않았습니다. 데모 모드로 실행됩니다.")
            self.is_demo_mode = True
        
        # [에이전트 초기화]
        if SMOLAGENTS_AVAILABLE and not self.is_demo_mode:
            try:
                self._initialize_agent()
                logger.info(f"[Research Agent] 사용자 {user_id}를 위한 리서치 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"[Research Agent] 에이전트 초기화 실패: {str(e)}")
                self.is_demo_mode = True
        else:
            self.is_demo_mode = True
            logger.info(f"[Research Agent] 사용자 {user_id}를 위한 데모 모드 리서치 에이전트 준비 완료")
    
    def _initialize_agent(self):
        """
        [리서치 에이전트 실제 초기화]
        정보 수집에 특화된 도구와 프롬프트로 에이전트 구성
        """
        try:
            # [LLM 모델 설정]
            model = LiteLLMModel(model_id="gpt-4o")
            logger.info("[Research Agent] LiteLLMModel 초기화 완료")
            
            # [전문 도구 설정] 정보 수집에 특화된 도구들만 제공
            research_tools = [
                search_internal,  # 사내 지식베이스 검색 (최우선)
                search_web       # 웹 검색 (보완적 사용)
            ]
            
            # [CodeAgent 생성] 리서치 전문 에이전트
            self.agent = CodeAgent(
                tools=research_tools,
                model=model,
                add_base_tools=True,
                verbosity_level=1
            )
            
            logger.info("[Research Agent] 리서치 전문 CodeAgent 생성 완료")
            
        except Exception as e:
            logger.error(f"[Research Agent] 에이전트 초기화 중 오류 발생: {str(e)}")
            raise
    
    def research(self, query: str) -> str:
        """
        [정보 수집 실행]
        주어진 질의에 대해 체계적인 정보 수집을 수행
        
        Args:
            query (str): 리서치 질의
            
        Returns:
            str: 수집된 정보 보고서
        """
        logger.info(f"[Research Agent] 정보 수집 작업 시작 - 질의: {query}")
        
        # [협업 로그 기록]
        AGENT_SESSION_STATE["collaboration_log"].append({
            "timestamp": datetime.now().isoformat(),
            "agent": "ResearchAgent",
            "action": "정보 수집 시작",
            "query": query
        })
        
        try:
            if self.is_demo_mode:
                return self._generate_demo_research(query)
            else:
                return self._execute_research(query)
                
        except Exception as e:
            logger.error(f"[Research Agent] 정보 수집 중 오류 발생: {str(e)}")
            return f"❌ **리서치 오류**\n\n정보 수집 중 오류가 발생했습니다: {str(e)}"
    
    def _execute_research(self, query: str) -> str:
        """
        [실제 리서치 실행]
        AI 에이전트를 통한 실제 정보 수집 수행
        """
        try:
            # [리서치 전문 프롬프트]
            research_prompt = f"""
당신은 금융 리서치 전문가입니다. 다음 원칙을 반드시 준수하세요:

1. **사내 데이터 우선**: 반드시 search_internal을 먼저 사용하여 사내 지식베이스를 검색하세요.
2. **외부 데이터 보완**: 사내 데이터가 부족한 경우에만 search_web을 사용하세요.
3. **객관적 수집**: 사실에 입각한 정보만 수집하고, 추측이나 의견은 배제하세요.
4. **출처 명시**: 모든 정보의 출처를 명확히 밝히세요.
5. **구조화된 보고**: 수집된 정보를 체계적으로 정리하여 보고하세요.

현재 사용 가능한 도구:
- search_internal: 사내 지식베이스 검색 (최우선 사용)
- search_web: 웹 검색 (보완적 사용)

리서치 요청: {query}

위 요청에 대해 체계적으로 정보를 수집하고 구조화된 보고서를 작성해주세요.
"""
            
            # [에이전트 실행]
            response = self.agent.run(research_prompt)
            
            # [결과 저장] 세션 상태에 리서치 결과 저장
            research_result = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "findings": str(response),
                "agent": "ResearchAgent"
            }
            AGENT_SESSION_STATE["research_results"].append(research_result)
            
            # [협업 로그 업데이트]
            AGENT_SESSION_STATE["collaboration_log"].append({
                "timestamp": datetime.now().isoformat(),
                "agent": "ResearchAgent", 
                "action": "정보 수집 완료",
                "result_length": len(str(response))
            })
            
            logger.info(f"[Research Agent] 정보 수집 완료 - 응답 길이: {len(str(response))}자")
            return str(response)
            
        except Exception as e:
            logger.error(f"[Research Agent] AI 에이전트 실행 중 오류: {str(e)}")
            return f"❌ **리서치 에이전트 오류**\n\n처리 중 오류가 발생했습니다: {str(e)}"
    
    def _generate_demo_research(self, query: str) -> str:
        """
        [데모 리서치 응답 생성]
        API 키가 없는 교육 환경에서 리서치 에이전트의 동작을 시뮬레이션
        """
        logger.info(f"[Research Agent] 데모 모드 리서치 응답 생성 - 질의: {query[:50]}...")
        
        # [데모 결과 저장]
        demo_result = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "findings": f"데모 모드 리서치 결과: {query}",
            "agent": "ResearchAgent"
        }
        AGENT_SESSION_STATE["research_results"].append(demo_result)
        
        return f"""# 🔍 리서치 에이전트 보고서 (데모 모드)

**질의**: {query}

## 📋 수집된 정보

### 🏢 사내 데이터베이스 검색 결과
- **검색 상태**: 데모 모드 시뮬레이션
- **관련 문서**: 사내 리포트 3건 발견 (시뮬레이션)
- **주요 내용**: 관련 분석 자료 및 과거 연구 결과

### 🌐 외부 정보 수집 결과  
- **웹 검색**: 최신 뉴스 및 시장 동향 정보
- **신뢰도**: 출처 검증 완료
- **업데이트**: 실시간 정보 반영

## 📊 정보 요약
실제 운영 환경에서는 다음과 같은 상세 정보를 제공합니다:
- 사내 지식베이스의 관련 문서 전문
- 검증된 외부 소스의 최신 정보
- 정보의 신뢰도 및 출처 평가

---
⚠️ **데모 모드**: 실제 정보 수집을 위해서는 OpenAI API 키 설정이 필요합니다.
"""


class MarketAnalystAgent:
    """
    [시장 데이터 분석가] Market Analyst Agent
    
    역할: 수치 데이터를 분석하는 애널리스트
    전문 분야: 주가 분석, 시장 현황 해석, 재무 지표 분석
    사용 도구: get_stock_price, get_market_summary
    
    특징:
    - 정량적 데이터 분석에 특화
    - 주가 추이와 시장 흐름 해석
    - 차트 데이터를 UI에서 활용할 수 있도록 구조화
    """
    
    def __init__(self, user_id: str):
        """
        [시장 분석 에이전트 초기화]
        
        Args:
            user_id (str): 사용자 ID
        """
        self.user_id = user_id
        self.agent = None
        self.is_demo_mode = False
        
        # [OpenAI API 키 확인]
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key or openai_api_key.startswith('your_'):
            logger.warning("[Market Analyst] OpenAI API 키가 설정되지 않았습니다. 데모 모드로 실행됩니다.")
            self.is_demo_mode = True
        
        # [에이전트 초기화]
        if SMOLAGENTS_AVAILABLE and not self.is_demo_mode:
            try:
                self._initialize_agent()
                logger.info(f"[Market Analyst] 사용자 {user_id}를 위한 시장 분석 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"[Market Analyst] 에이전트 초기화 실패: {str(e)}")
                self.is_demo_mode = True
        else:
            self.is_demo_mode = True
            logger.info(f"[Market Analyst] 사용자 {user_id}를 위한 데모 모드 시장 분석 에이전트 준비 완료")
    
    def _initialize_agent(self):
        """
        [시장 분석 에이전트 실제 초기화]
        시장 데이터 분석에 특화된 도구와 프롬프트로 에이전트 구성
        """
        try:
            # [LLM 모델 설정]
            model = LiteLLMModel(model_id="gpt-4o")
            logger.info("[Market Analyst] LiteLLMModel 초기화 완료")
            
            # [전문 도구 설정] 시장 데이터 분석에 특화된 도구들만 제공
            analyst_tools = [
                get_stock_price,     # 주가 정보 조회
                get_market_summary   # 시장 현황 요약
            ]
            
            # [CodeAgent 생성] 시장 분석 전문 에이전트
            self.agent = CodeAgent(
                tools=analyst_tools,
                model=model,
                add_base_tools=True,
                verbosity_level=1
            )
            
            logger.info("[Market Analyst] 시장 분석 전문 CodeAgent 생성 완료")
            
        except Exception as e:
            logger.error(f"[Market Analyst] 에이전트 초기화 중 오류 발생: {str(e)}")
            raise
    
    def analyze(self, query: str) -> str:
        """
        [시장 데이터 분석 실행]
        주어진 질의에 대해 정량적 시장 분석을 수행
        
        Args:
            query (str): 분석 질의
            
        Returns:
            str: 분석 결과 보고서
        """
        logger.info(f"[Market Analyst] 시장 분석 작업 시작 - 질의: {query}")
        
        # [협업 로그 기록]
        AGENT_SESSION_STATE["collaboration_log"].append({
            "timestamp": datetime.now().isoformat(),
            "agent": "MarketAnalystAgent",
            "action": "시장 분석 시작",
            "query": query
        })
        
        try:
            if self.is_demo_mode:
                return self._generate_demo_analysis(query)
            else:
                return self._execute_analysis(query)
                
        except Exception as e:
            logger.error(f"[Market Analyst] 시장 분석 중 오류 발생: {str(e)}")
            return f"❌ **분석 오류**\n\n시장 분석 중 오류가 발생했습니다: {str(e)}"
    
    def _execute_analysis(self, query: str) -> str:
        """
        [실제 시장 분석 실행]
        AI 에이전트를 통한 실제 시장 데이터 분석 수행
        """
        try:
            # [시장 분석 전문 프롬프트]
            analysis_prompt = f"""
당신은 수치 데이터를 분석하는 시장 애널리스트입니다. 다음 원칙을 반드시 준수하세요:

1. **정량적 분석**: 주가, 거래량, 시장 지수 등 수치 데이터를 중심으로 분석하세요.
2. **추세 해석**: 주가 추이와 시장 흐름을 객관적으로 해석하세요.
3. **비교 분석**: 동종 업계나 시장 전체와의 비교를 통해 상대적 위치를 파악하세요.
4. **리스크 평가**: 변동성, 거래량 등을 통해 투자 리스크를 평가하세요.
5. **데이터 기반**: 추측이나 감정적 판단을 배제하고 데이터에 기반한 분석을 수행하세요.

현재 사용 가능한 도구:
- get_stock_price: 실시간 주가 정보 조회
- get_market_summary: 주요 지수 및 시장 현황 요약

분석 요청: {query}

위 요청에 대해 정량적 데이터를 수집하고 전문적인 시장 분석을 수행해주세요.
"""
            
            # [에이전트 실행]
            response = self.agent.run(analysis_prompt)
            
            # [결과 저장] 세션 상태에 분석 결과 저장
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "analysis": str(response),
                "agent": "MarketAnalystAgent"
            }
            AGENT_SESSION_STATE["analysis_results"].append(analysis_result)
            
            # [협업 로그 업데이트]
            AGENT_SESSION_STATE["collaboration_log"].append({
                "timestamp": datetime.now().isoformat(),
                "agent": "MarketAnalystAgent",
                "action": "시장 분석 완료",
                "result_length": len(str(response))
            })
            
            logger.info(f"[Market Analyst] 시장 분석 완료 - 응답 길이: {len(str(response))}자")
            return str(response)
            
        except Exception as e:
            logger.error(f"[Market Analyst] AI 에이전트 실행 중 오류: {str(e)}")
            return f"❌ **시장 분석 에이전트 오류**\n\n처리 중 오류가 발생했습니다: {str(e)}"
    
    def _generate_demo_analysis(self, query: str) -> str:
        """
        [데모 시장 분석 응답 생성]
        API 키가 없는 교육 환경에서 시장 분석 에이전트의 동작을 시뮬레이션
        """
        logger.info(f"[Market Analyst] 데모 모드 시장 분석 응답 생성 - 질의: {query[:50]}...")
        
        # [데모 결과 저장]
        demo_result = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "analysis": f"데모 모드 시장 분석 결과: {query}",
            "agent": "MarketAnalystAgent"
        }
        AGENT_SESSION_STATE["analysis_results"].append(demo_result)
        
        return f"""# 📈 시장 분석 에이전트 보고서 (데모 모드)

**분석 대상**: {query}

## 📊 정량적 분석 결과

### 💰 주가 정보 (시뮬레이션)
- **현재가**: 75,000원 (데모 데이터)
- **전일대비**: +1,500원 (+2.04%)
- **거래량**: 1,234,567주
- **시가총액**: 45조원

### 📈 기술적 분석
- **추세**: 상승 추세 지속 (데모)
- **지지선**: 72,000원
- **저항선**: 78,000원
- **RSI**: 65.4 (중립)

### 🏦 시장 현황
- **코스피**: 2,450.32 (+0.85%)
- **코스닥**: 850.45 (+1.23%)
- **섹터 순위**: 반도체 업종 2위

## 📋 분석 요약
실제 운영 환경에서는 다음과 같은 상세 분석을 제공합니다:
- 실시간 주가 데이터 및 차트 분석
- 동종 업계 비교 분석
- 재무 지표 기반 밸류에이션
- 리스크 요인 및 투자 포인트

---
⚠️ **데모 모드**: 실제 시장 분석을 위해서는 OpenAI API 키 설정이 필요합니다.
"""


class ManagerAgent:
    """
    [프로젝트 매니저] Manager Agent
    
    역할: 프로젝트 매니저 및 오케스트레이터
    전문 분야: 하위 에이전트 관리, 업무 분담, 최종 보고서 작성
    사용 도구: ResearchAgent, MarketAnalystAgent (Tool.from_agent로 변환), save_report
    
    특징:
    - 사용자 요청을 분석하여 적절한 하위 에이전트에게 업무 분담
    - 각 에이전트의 결과를 취합하여 종합적인 보고서 작성
    - 전체 프로세스를 조율하고 품질을 관리
    """
    
    def __init__(self, user_id: str):
        """
        [매니저 에이전트 초기화]
        
        Args:
            user_id (str): 사용자 ID
        """
        self.user_id = user_id
        self.agent = None
        self.is_demo_mode = False
        
        # [하위 에이전트 초기화]
        self.research_agent = ResearchAgent(user_id)
        self.analyst_agent = MarketAnalystAgent(user_id)
        
        # [OpenAI API 키 확인]
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key or openai_api_key.startswith('your_'):
            logger.warning("[Manager Agent] OpenAI API 키가 설정되지 않았습니다. 데모 모드로 실행됩니다.")
            self.is_demo_mode = True
        
        # [에이전트 초기화]
        if SMOLAGENTS_AVAILABLE and not self.is_demo_mode:
            try:
                self._initialize_agent()
                logger.info(f"[Manager Agent] 사용자 {user_id}를 위한 매니저 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"[Manager Agent] 에이전트 초기화 실패: {str(e)}")
                self.is_demo_mode = True
        else:
            self.is_demo_mode = True
            logger.info(f"[Manager Agent] 사용자 {user_id}를 위한 데모 모드 매니저 에이전트 준비 완료")
    
    def _initialize_agent(self):
        """
        [매니저 에이전트 실제 초기화]
        하위 에이전트들을 도구로 변환하여 매니저가 호출할 수 있도록 구성
        """
        try:
            # [LLM 모델 설정]
            model = LiteLLMModel(model_id="gpt-4o")
            logger.info("[Manager Agent] LiteLLMModel 초기화 완료")
            
            # [매니저 전용 도구 설정]
            # 매니저는 리포트 저장과 기본 도구들을 사용
            manager_tools = [save_report]
            
            # [CodeAgent 생성] 매니저 전문 에이전트
            self.agent = CodeAgent(
                tools=manager_tools,
                model=model,
                add_base_tools=True,
                verbosity_level=1
            )
            
            logger.info("[Manager Agent] 매니저 전문 CodeAgent 생성 완료")
            
        except Exception as e:
            logger.error(f"[Manager Agent] 에이전트 초기화 중 오류 발생: {str(e)}")
            raise
    
    def manage_request(self, request: str) -> str:
        """
        [요청 관리 및 처리]
        사용자 요청을 분석하여 적절한 하위 에이전트에게 업무를 분담하고 결과를 취합
        
        Args:
            request (str): 사용자 요청
            
        Returns:
            str: 종합 보고서
        """
        logger.info(f"[Manager Agent] 요청 관리 시작 - 요청: {request}")
        
        # [협업 로그 기록]
        AGENT_SESSION_STATE["collaboration_log"].append({
            "timestamp": datetime.now().isoformat(),
            "agent": "ManagerAgent",
            "action": "요청 관리 시작",
            "request": request
        })
        
        try:
            if self.is_demo_mode:
                return self._generate_demo_management(request)
            else:
                return self._execute_management(request)
                
        except Exception as e:
            logger.error(f"[Manager Agent] 요청 관리 중 오류 발생: {str(e)}")
            return f"❌ **매니저 오류**\n\n요청 관리 중 오류가 발생했습니다: {str(e)}"
    
    def _execute_management(self, request: str) -> str:
        """
        [실제 요청 관리 실행]
        AI 매니저 에이전트를 통한 실제 업무 분담 및 조율 수행
        """
        try:
            # [1단계: 리서처에게 정보 수집 요청]
            logger.info("[Manager Agent] 하위 에이전트 호출 - 리서처")
            research_result = self.research_agent.research(request)
            
            # [2단계: 애널리스트에게 분석 요청]
            logger.info("[Manager Agent] 하위 에이전트 호출 - 애널리스트")
            analysis_result = self.market_analyst.analyze(request)
            
            # [3단계: 매니저가 결과 취합 및 최종 보고서 작성]
            management_prompt = f"""
당신은 금융 리서치 팀장입니다. 팀원들의 작업 결과를 바탕으로 최종 보고서를 작성하세요.

**리서처 보고서:**
{research_result}

**애널리스트 보고서:**
{analysis_result}

**사용자 요청:** {request}

위 정보들을 종합하여 완성도 높은 최종 보고서를 작성해주세요. 
정보의 정확성을 검증하고, 객관적인 분석을 제공하며, 실행 가능한 인사이트를 포함하세요.
"""
            
            # [에이전트 실행]
            response = self.agent.run(management_prompt)
            
            # [협업 로그 업데이트]
            AGENT_SESSION_STATE["collaboration_log"].append({
                "timestamp": datetime.now().isoformat(),
                "agent": "ManagerAgent",
                "action": "요청 관리 완료",
                "result_length": len(str(response))
            })
            
            logger.info(f"[Manager Agent] 요청 관리 완료 - 응답 길이: {len(str(response))}자")
            return str(response)
            
        except Exception as e:
            logger.error(f"[Manager Agent] AI 에이전트 실행 중 오류: {str(e)}")
            return f"❌ **매니저 에이전트 오류**\n\n처리 중 오류가 발생했습니다: {str(e)}"
    
    def _execute_demo_collaboration(self, request: str) -> str:
        """
        [데모 모드 협업 시뮬레이션]
        하위 에이전트들과의 협업 과정을 데모 모드로 시뮬레이션
        """
        logger.info("[Manager Agent] 데모 모드 협업 시뮬레이션 시작")
        
        # [1단계: 리서처에게 정보 수집 요청]
        logger.info("[Manager Agent] 하위 에이전트 호출 - 리서처")
        research_result = self.research_agent.research(request)
        
        # [2단계: 애널리스트에게 분석 요청]
        logger.info("[Manager Agent] 하위 에이전트 호출 - 애널리스트")
        analysis_result = self.analyst_agent.analyze(request)
        
        # [3단계: 결과 취합]
        combined_report = f"""# 🏦 Quant-X 종합 리서치 보고서 (데모 모드)

**요청**: {request}
**작성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**팀장**: {self.user_id}

---

## 📋 팀 협업 과정

### 1️⃣ 정보 수집 단계 (리서처)
{research_result}

---

### 2️⃣ 시장 분석 단계 (애널리스트)  
{analysis_result}

---

## 🎯 종합 결론

위 팀원들의 작업 결과를 종합하면:

### 📊 주요 발견사항
- **정보 수집**: 리서처가 사내외 데이터를 체계적으로 수집
- **정량 분석**: 애널리스트가 시장 데이터를 객관적으로 분석
- **협업 효과**: 각 전문가의 강점을 활용한 시너지 창출

### 💡 투자 시사점
- 수집된 정보와 분석 결과를 종합한 객관적 평가
- 리스크 요인과 기회 요소의 균형적 검토
- 데이터 기반의 합리적 투자 판단 근거 제시

---

⚠️ **투자 유의사항**: 본 보고서는 데모용이며, 실제 투자 결정에 사용하지 마세요.
투자에는 원금 손실 위험이 있으며, 충분한 검토 후 신중한 결정을 권장합니다.
"""
        
        return combined_report
    
    def _generate_demo_management(self, request: str) -> str:
        """
        [데모 매니저 응답 생성]
        API 키가 없는 교육 환경에서 매니저 에이전트의 동작을 시뮬레이션
        """
        logger.info(f"[Manager Agent] 데모 모드 매니저 응답 생성 - 요청: {request[:50]}...")
        
        # [데모 모드에서도 실제 하위 에이전트 호출하여 협업 시뮬레이션]
        return self._execute_demo_collaboration(request)


class QuantXMultiAgent:
    """
    [멀티 에이전트 시스템] Quant-X Multi-Agent System
    
    Manager-Worker 패턴을 구현한 멀티 에이전트 협업 시스템
    기존 단일 QuantXAgent를 대체하여 역할별 전문화된 에이전트들이 협업
    
    구성 요소:
    - ManagerAgent: 전체 프로세스 조율 및 최종 보고서 작성
    - ResearchAgent: 정보 수집 전문가
    - MarketAnalystAgent: 시장 데이터 분석가
    
    특징:
    - 각 에이전트의 전문성을 활용한 고품질 결과 생성
    - 실시간 협업 과정 로그를 통한 투명성 확보
    - UI에서 활용할 수 있는 중간 산출물 저장
    """
    
    def __init__(self, user_id: str):
        """
        [멀티 에이전트 시스템 초기화]
        
        Args:
            user_id (str): 사용자 ID
        """
        self.user_id = user_id
        self.manager_agent = ManagerAgent(user_id)
        self.is_demo_mode = self.manager_agent.is_demo_mode
        
        logger.info(f"[Multi-Agent System] 사용자 {user_id}를 위한 멀티 에이전트 시스템 초기화 완료")
        
        # [세션 상태 초기화]
        AGENT_SESSION_STATE["collaboration_log"].append({
            "timestamp": datetime.now().isoformat(),
            "agent": "QuantXMultiAgent",
            "action": "시스템 초기화 완료",
            "user_id": user_id
        })
    
    def process_request(self, request: str) -> str:
        """
        [요청 처리]
        사용자 요청을 매니저 에이전트에게 전달하여 멀티 에이전트 협업 프로세스 시작
        
        Args:
            request (str): 사용자 요청
            
        Returns:
            str: 멀티 에이전트 협업 결과
        """
        logger.info(f"[Multi-Agent System] 요청 처리 시작 - 사용자: {self.user_id}")
        
        try:
            # [매니저 에이전트에게 요청 위임]
            result = self.manager_agent.manage_request(request)
            
            logger.info(f"[Multi-Agent System] 멀티 에이전트 협업 완료")
            return result
            
        except Exception as e:
            logger.error(f"[Multi-Agent System] 요청 처리 중 오류 발생: {str(e)}")
            return f"❌ **멀티 에이전트 시스템 오류**\n\n요청 처리 중 오류가 발생했습니다: {str(e)}"
    
    def get_collaboration_log(self) -> List[Dict]:
        """
        [협업 로그 조회]
        멀티 에이전트 간 협업 과정을 기록한 로그를 반환
        
        Returns:
            List[Dict]: 협업 과정 로그
        """
        return AGENT_SESSION_STATE["collaboration_log"]
    
    def get_intermediate_results(self) -> Dict:
        """
        [중간 산출물 조회]
        각 에이전트가 생성한 중간 산출물을 반환 (UI에서 활용)
        
        Returns:
            Dict: 중간 산출물 딕셔너리
        """
        return {
            "research_results": AGENT_SESSION_STATE["research_results"],
            "analysis_results": AGENT_SESSION_STATE["analysis_results"],
            "intermediate_outputs": AGENT_SESSION_STATE["intermediate_outputs"]
        }


def create_agent(user_id: str) -> QuantXMultiAgent:
    """
    [멀티 에이전트 팩토리 함수]
    사용자 ID를 받아 해당 사용자를 위한 QuantX 멀티 에이전트 시스템 인스턴스를 생성
    
    Args:
        user_id (str): 사용자 식별자
        
    Returns:
        QuantXMultiAgent: 초기화된 멀티 에이전트 시스템 인스턴스
    """
    logger.info(f"[Multi-Agent System] 사용자 {user_id}를 위한 새 멀티 에이전트 시스템 생성 요청")
    return QuantXMultiAgent(user_id)


def get_session_state() -> Dict:
    """
    [세션 상태 조회]
    현재 멀티 에이전트 세션의 상태를 반환 (UI 연동용)
    
    Returns:
        Dict: 현재 세션 상태
    """
    return AGENT_SESSION_STATE


def clear_session_state():
    """
    [세션 상태 초기화]
    멀티 에이전트 세션 상태를 초기화 (새 세션 시작 시 사용)
    """
    global AGENT_SESSION_STATE
    AGENT_SESSION_STATE = {
        "research_results": [],
        "analysis_results": [],
        "intermediate_outputs": {},
        "collaboration_log": []
    }
    logger.info("[Multi-Agent System] 세션 상태 초기화 완료")