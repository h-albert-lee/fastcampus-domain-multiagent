"""
[Agent Core] AI 에이전트 핵심 로직

이 모듈은 smolagents의 CodeAgent를 활용하여 금융 리서치 전문가 AI를 구현합니다.
CodeAgent는 Python 코드를 생성하여 논리적으로 문제를 해결하는 능력이 뛰어나
복잡한 금융 분석 작업에 적합합니다.

교육 목표:
- smolagents CodeAgent의 활용법 학습
- 금융 도메인에 특화된 System Prompt 설계
- 도구 통합 및 에이전트 실행 파이프라인 구현
- 에러 처리 및 안전한 에이전트 운영 방법 이해
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# [smolagents] AI 에이전트 프레임워크
from smolagents import CodeAgent
try:
    from smolagents import HfApiModel
except ImportError:
    from smolagents import ApiModel as HfApiModel

# [Governance Layer] 보안 및 권한 관리
from core.auth import auth_manager
from core.logger import audit_logger
from core.guardrails import security_guardrails

# [Agent Tools] 에이전트가 사용할 도구들
from agents.tools import (
    search_internal, search_web, get_stock_price, 
    save_report, get_market_summary, get_available_tools_for_user
)

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)

class QuantXAgent:
    """
    [Quant-X Agent] 금융 리서치 전문 AI 에이전트
    
    금융 엔터프라이즈 환경에서 동작하는 AI 에이전트로,
    엄격한 보안 정책과 규제 준수 하에 금융 리서치 업무를 수행합니다.
    """
    
    def __init__(self):
        """
        [Agent Initialization] 에이전트 초기화
        """
        self.agent = None
        self.logger = logging.getLogger(__name__)
        self._initialize_agent()
    
    def _initialize_agent(self):
        """
        [Agent Setup] CodeAgent 초기화 및 설정
        
        금융 도메인에 특화된 System Prompt와 도구를 설정합니다.
        """
        try:
            # [OpenAI API Key] API 키 확인
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key or openai_api_key == "your_openai_api_key_here":
                self.logger.warning("[Agent Core] OpenAI API 키가 설정되지 않았습니다. 데모 모드로 실행됩니다.")
                # 교육 목적으로 더미 에이전트 생성
                self.agent = None
                return
            
            # [Model Configuration] 모델 설정
            # 실제 운영에서는 HfApiModel 대신 OpenAI 모델을 직접 사용할 수 있습니다.
            model = HfApiModel(model_id="gpt-3.5-turbo")  # 또는 gpt-4
            
            # [System Prompt] 금융 리서치 전문가 역할 정의
            system_prompt = self._create_system_prompt()
            
            # [Tools] 에이전트가 사용할 도구 목록
            tools = [
                search_internal,
                search_web, 
                get_stock_price,
                save_report,
                get_market_summary
            ]
            
            # [CodeAgent] 코드 에이전트 생성
            self.agent = CodeAgent(
                tools=tools,
                model=model,
                system_prompt=system_prompt,
                max_iterations=10,  # 최대 반복 횟수 제한 (무한 루프 방지)
                verbosity_level=1   # 로그 레벨 (0: 최소, 2: 최대)
            )
            
            self.logger.info("[Agent Core] Quant-X 에이전트 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"[Agent Core] 에이전트 초기화 실패: {e}")
            raise
    
    def _create_system_prompt(self) -> str:
        """
        [System Prompt] 금융 리서치 전문가 시스템 프롬프트 생성
        
        에이전트의 역할, 행동 원칙, 작업 절차를 명확히 정의합니다.
        
        Returns:
            str: 시스템 프롬프트 텍스트
        """
        return """당신은 **Quant-X 금융 리서치 전문가**입니다.

## 🎯 역할 및 책임
- 금융 시장 분석 및 투자 정보 제공
- 사실에 기반한 객관적이고 전문적인 리서치 수행
- 규제 준수 및 투자자 보호 원칙 준수

## 📋 작업 절차 (반드시 순서대로 수행)
1. **사내 데이터 우선 검색**: 모든 질문에 대해 먼저 `search_internal`을 사용하여 사내 지식베이스를 검색하세요.
2. **외부 정보 보완**: 사내 데이터가 부족한 경우에만 `search_web`으로 외부 정보를 수집하세요.
3. **실시간 데이터 활용**: 주가나 시장 정보가 필요한 경우 `get_stock_price`, `get_market_summary`를 활용하세요.
4. **종합 분석**: 수집된 정보를 바탕으로 논리적이고 체계적인 분석을 수행하세요.
5. **리포트 작성**: 권한이 있는 경우 `save_report`로 분석 결과를 저장하세요.

## ⚖️ 준수 사항
- **불완전 판매 금지**: "확실한", "보장", "무조건" 등의 표현 사용 금지
- **투자 권유 금지**: 직접적인 매수/매도 권유 대신 "참고용 정보" 제공
- **위험 고지**: 모든 투자 관련 정보에 위험성 명시
- **출처 명시**: 모든 정보의 출처를 명확히 표기

## 💬 응답 스타일
- **전문적이고 객관적인 어조** 사용
- **구조화된 형태**로 정보 제공 (제목, 소제목, 불릿 포인트 활용)
- **한국어**로 응답 (전문 용어는 한글과 영문 병기)
- **데이터 기반** 분석 및 의견 제시

## 🚫 금지 사항
- 개인적 의견이나 추측성 발언
- 확실성을 나타내는 단정적 표현
- 직접적인 투자 권유나 종목 추천
- 근거 없는 주장이나 루머 전파

## 🔧 도구 사용 가이드
- `search_internal`: 사내 공시, 리포트 등 검증된 정보 검색
- `search_web`: 최신 뉴스, 시장 동향 등 외부 정보 수집
- `get_stock_price`: 실시간 주가 및 기업 정보 조회
- `get_market_summary`: 주요 지수 및 시장 현황 파악
- `save_report`: 분석 결과 리포트 저장 (권한 필요)

모든 작업은 금융 규제와 사내 정책을 준수하며 수행하세요."""
    
    def _generate_demo_response(self, user_request: str) -> str:
        """
        [Demo Response] 데모 응답 생성
        
        OpenAI API 키가 없을 때 교육 목적으로 사용하는 더미 응답을 생성합니다.
        
        Args:
            user_request (str): 사용자 요청
            
        Returns:
            str: 데모 응답
        """
        return f"""
# 📊 Quant-X 데모 응답

**요청**: {user_request}

## 🔍 분석 결과

안녕하세요! 현재 **데모 모드**로 실행 중입니다. 

실제 운영 환경에서는 다음과 같은 분석을 제공합니다:

### 📈 주요 분석 내용
- **사내 데이터베이스 검색**: 관련 공시 및 리포트 정보
- **실시간 주가 정보**: Yahoo Finance API를 통한 최신 데이터
- **시장 동향 분석**: 주요 지수 및 섹터별 현황
- **전문가 의견**: AI 기반 종합 분석 및 전망

### 🛡️ 보안 및 규제 준수
- 모든 정보는 금융감독원 규정에 따라 제공됩니다
- 투자 권유가 아닌 참고용 정보입니다
- 투자 결정은 본인의 책임하에 이루어져야 합니다

### 🔧 시스템 설정
실제 AI 에이전트를 사용하려면:
1. `.env` 파일에 `OPENAI_API_KEY` 설정
2. 시스템 재시작

---
⚠️ **투자 유의사항**: 본 정보는 데모용이며, 실제 투자 결정에 사용하지 마세요.
"""
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        [Request Processing] 사용자 요청 처리
        
        보안 가드레일 -> 에이전트 실행 -> 출력 필터링 파이프라인을 수행합니다.
        
        Args:
            user_request (str): 사용자 요청
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        # [User Session] 현재 사용자 정보
        user_session = auth_manager.get_current_user()
        user_id = user_session.user_id if user_session else "anonymous"
        
        # [Request Logging] 요청 로깅
        audit_logger.log_audit(
            user_id=user_id,
            action="AGENT_REQUEST",
            details={
                "request_length": len(user_request),
                "request_preview": user_request[:200] + "..." if len(user_request) > 200 else user_request
            }
        )
        
        try:
            # [Phase 1] 입력 보안 검사
            self.logger.info("[Agent Core] 1단계: 입력 보안 검사")
            input_check = security_guardrails.check_input(user_request, user_id)
            
            if not input_check.is_safe:
                return {
                    "success": False,
                    "phase": "input_validation",
                    "message": input_check.message,
                    "issues": input_check.detected_issues,
                    "response": "요청이 보안 정책에 위배되어 처리할 수 없습니다."
                }
            
            # [Phase 2] 에이전트 실행
            self.logger.info("[Agent Core] 2단계: AI 에이전트 실행")
            
            # 에이전트가 초기화되지 않은 경우 더미 응답
            if self.agent is None:
                agent_response = self._generate_demo_response(user_request)
            else:
                # 사용자 권한 정보를 에이전트에게 제공
                user_info = auth_manager.get_user_info()
                context_prompt = f"""
현재 사용자 정보:
- 사용자 ID: {user_info['user_id']}
- 역할: {user_info.get('role_display', 'N/A')}
- 사용 가능한 도구: {[tool['name'] for tool in get_available_tools_for_user()]}

사용자 요청: {user_request}
"""
                
                # 에이전트 실행
                agent_response = self.agent.run(context_prompt)
            
            # [Phase 3] 출력 필터링
            self.logger.info("[Agent Core] 3단계: 출력 보안 검사")
            output_check = security_guardrails.filter_output(str(agent_response), user_id)
            
            if not output_check.is_safe:
                return {
                    "success": False,
                    "phase": "output_filtering", 
                    "message": output_check.message,
                    "issues": output_check.detected_issues,
                    "response": "응답에 민감 정보가 포함되어 제공할 수 없습니다."
                }
            
            # [Success Response] 성공 응답
            final_response = output_check.filtered_content or str(agent_response)
            
            # [Success Logging] 성공 로깅
            audit_logger.log_audit(
                user_id=user_id,
                action="AGENT_SUCCESS",
                details={
                    "response_length": len(final_response),
                    "input_issues": len(input_check.detected_issues),
                    "output_issues": len(output_check.detected_issues)
                }
            )
            
            return {
                "success": True,
                "phase": "completed",
                "message": "요청이 성공적으로 처리되었습니다.",
                "response": final_response,
                "metadata": {
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "input_safe": input_check.is_safe,
                    "output_filtered": len(output_check.detected_issues) > 0,
                    "compliance_score": security_guardrails.check_compliance_score(final_response)
                }
            }
            
        except Exception as e:
            # [Error Handling] 에러 처리
            self.logger.error(f"[Agent Core] 요청 처리 실패: {e}")
            
            audit_logger.log_security_event(
                user_id=user_id,
                event_type="AGENT_ERROR",
                message="에이전트 실행 오류",
                severity="WARNING",
                details={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            return {
                "success": False,
                "phase": "execution_error",
                "message": "요청 처리 중 오류가 발생했습니다.",
                "response": f"시스템 오류가 발생했습니다. 관리자에게 문의하세요.\n\n오류 정보: {str(e)}",
                "error": str(e)
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        [Agent Status] 에이전트 상태 정보
        
        Returns:
            Dict[str, Any]: 에이전트 상태 정보
        """
        user_session = auth_manager.get_current_user()
        available_tools = get_available_tools_for_user()
        
        return {
            "agent_initialized": self.agent is not None,
            "current_user": user_session.user_id if user_session else None,
            "user_role": user_session.role.value if user_session else None,
            "available_tools": len(available_tools),
            "tool_list": [tool["name"] for tool in available_tools],
            "system_status": "정상",
            "last_check": datetime.now().isoformat()
        }
    
    def reset_agent(self):
        """
        [Agent Reset] 에이전트 재초기화
        
        문제 발생 시 에이전트를 재초기화합니다.
        """
        try:
            self.logger.info("[Agent Core] 에이전트 재초기화 시작")
            self._initialize_agent()
            self.logger.info("[Agent Core] 에이전트 재초기화 완료")
            
            # 시스템 이벤트 로깅
            audit_logger.log_system_event(
                "AGENT_RESET",
                "에이전트 재초기화 완료"
            )
            
        except Exception as e:
            self.logger.error(f"[Agent Core] 에이전트 재초기화 실패: {e}")
            raise


# [Global Instance] 전역 에이전트 인스턴스
# 앱 전체에서 하나의 에이전트를 공유합니다.
quantx_agent = QuantXAgent()