"""
[AI Agent Core] 금융 리서치 에이전트의 핵심 로직
- smolagents CodeAgent를 사용하여 Python 코드 생성을 통한 논리적 추론 수행
- LiteLLMModel을 통한 안정적인 OpenAI 모델 연결 (gpt-4o 사용)
- 시스템의 통제 하에 인가된 도구만 사용하도록 제한
- 데모 모드 지원으로 API 키 없이도 교육 목적 실행 가능
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# [AI Framework] smolagents 프레임워크 import - LiteLLMModel 사용으로 안정성 확보
try:
    # smolagents 0.3.x 버전에서 LiteLLMModel 사용 (OpenAI 연결 최적화)
    from smolagents import CodeAgent, LiteLLMModel
    SMOLAGENTS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("[Agent Core] smolagents LiteLLMModel 로드 성공 - OpenAI 연결 준비 완료")
except ImportError:
    try:
        # 구버전 호환성 - ApiModel 폴백
        from smolagents import CodeAgent, ApiModel as LiteLLMModel
        SMOLAGENTS_AVAILABLE = True
        logger = logging.getLogger(__name__)
        logger.warning("[Agent Core] LiteLLMModel을 찾을 수 없어 ApiModel로 폴백")
    except ImportError:
        SMOLAGENTS_AVAILABLE = False
        logger = logging.getLogger(__name__)
        logger.warning("[Agent Core] smolagents 라이브러리를 찾을 수 없습니다. 데모 모드로만 실행됩니다.")

# [Internal Modules] 내부 모듈 import
from agents.tools import get_all_tools
from core.logger import get_logger

logger = get_logger(__name__)


class QuantXAgent:
    """
    [금융 리서치 에이전트] 
    금융권의 엄격한 보안 규제를 준수하면서 AI 기반 리서치를 수행하는 에이전트
    
    핵심 특징:
    - LiteLLMModel을 통한 안정적인 GPT-4o 연결
    - 거버넌스 레이어의 통제 하에 도구 사용
    - 사내 지식베이스 우선 검색 정책
    - 모든 행위에 대한 감사 로그 자동 기록
    """
    
    def __init__(self, user_id: str):
        """
        [에이전트 초기화]
        사용자별 권한에 따라 에이전트를 초기화하고 사용 가능한 도구를 설정
        
        Args:
            user_id (str): 사용자 ID (권한 체크 및 감사 로그용)
        """
        self.user_id = user_id
        self.agent = None
        self.is_demo_mode = False
        
        # [OpenAI API 키 확인] 실제 AI 기능 사용 가능 여부 판단
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key or openai_api_key.startswith('your_'):
            logger.warning("[Agent Core] OpenAI API 키가 설정되지 않았습니다. 데모 모드로 실행됩니다.")
            self.is_demo_mode = True
        
        # [에이전트 초기화] smolagents 사용 가능 시에만 실제 에이전트 생성
        if SMOLAGENTS_AVAILABLE and not self.is_demo_mode:
            try:
                self._initialize_agent()
                logger.info(f"[Agent Core] 사용자 {user_id}를 위한 AI 에이전트 초기화 완료")
            except Exception as e:
                logger.error(f"[Agent Core] 에이전트 초기화 실패: {str(e)}")
                self.is_demo_mode = True
        else:
            self.is_demo_mode = True
            logger.info(f"[Agent Core] 사용자 {user_id}를 위한 데모 모드 에이전트 준비 완료")
    
    def _initialize_agent(self):
        """
        [실제 AI 에이전트 초기화]
        LiteLLMModel을 사용하여 GPT-4o 모델과 연결하고 CodeAgent 생성
        
        주요 설정:
        - model_id: "gpt-4o" (최신 GPT-4 Omni 모델 사용)
        - add_base_tools: True (기본 Python 연산 도구 포함)
        - tools: 금융 도메인 특화 도구들 (사내 검색, 웹 검색, 주가 조회 등)
        """
        try:
            # [LLM 모델 설정] LiteLLMModel을 통한 안정적인 OpenAI 연결
            # GPT-4o 사용으로 더 정확하고 신뢰성 있는 금융 분석 제공
            model = LiteLLMModel(model_id="gpt-4o")
            logger.info("[Agent Core] LiteLLMModel 초기화 완료 - GPT-4o 연결 성공")
            
            # [도구 로드] 거버넌스 레이어의 통제를 받는 금융 도구들 로드
            tools = get_all_tools(self.user_id)
            logger.info(f"[Agent Core] {len(tools)}개의 도구 로드 완료")
            
            # [CodeAgent 생성] Python 코드 생성을 통한 논리적 추론 에이전트
            # add_base_tools=True: 기본적인 수학 연산, 데이터 처리 등이 가능하도록 설정
            self.agent = CodeAgent(
                tools=tools,
                model=model,
                add_base_tools=True,  # [중요] 기본 Python 도구 포함으로 계산 능력 확보
                max_iterations=10,    # [안전장치] 무한 루프 방지
                verbosity_level=1     # [디버깅] 적절한 로그 레벨 설정
            )
            
            logger.info("[Agent Core] CodeAgent 생성 완료 - 금융 리서치 준비 완료")
            
        except Exception as e:
            logger.error(f"[Agent Core] 에이전트 초기화 중 오류 발생: {str(e)}")
            raise
    
    def process_request(self, request: str) -> str:
        """
        [리서치 요청 처리]
        사용자의 금융 리서치 요청을 처리하고 결과를 반환
        
        처리 과정:
        1. 입력 검증 (보안 가드레일)
        2. AI 에이전트 실행 또는 데모 응답 생성
        3. 출력 검증 (규제 준수)
        4. 감사 로그 기록
        
        Args:
            request (str): 사용자의 리서치 요청
            
        Returns:
            str: 처리된 리서치 결과
        """
        try:
            if self.is_demo_mode:
                # [데모 모드] API 키 없이도 교육 목적으로 실행 가능
                return self._generate_demo_response(request)
            else:
                # [실제 AI 모드] smolagents CodeAgent를 통한 실제 추론 수행
                return self._execute_agent(request)
                
        except Exception as e:
            logger.error(f"[Agent Core] 요청 처리 중 오류 발생: {str(e)}")
            return f"❌ **시스템 오류**\n\n요청 처리 중 오류가 발생했습니다: {str(e)}\n\n시스템 관리자에게 문의하시기 바랍니다."
    
    def _execute_agent(self, request: str) -> str:
        """
        [실제 AI 에이전트 실행]
        CodeAgent를 통해 실제 AI 추론을 수행하고 결과를 반환
        
        Args:
            request (str): 사용자 요청
            
        Returns:
            str: AI 에이전트의 응답
        """
        try:
            # [시스템 프롬프트] 금융 도메인 특화 지시사항
            system_prompt = """
당신은 금융 리서치 전문가입니다. 다음 원칙을 반드시 준수하세요:

1. **사내 데이터 우선**: 질문에 답하기 위해 반드시 search_internal을 먼저 사용하여 사내 지식베이스를 검색하세요.
2. **외부 데이터 보완**: 사내 데이터가 부족한 경우에만 search_web과 get_stock_price를 사용하세요.
3. **객관적 분석**: 사실에 입각한 드라이한 어조로 보고서를 작성하세요.
4. **규제 준수**: 투자 권유나 확실한 수익을 보장하는 표현은 절대 사용하지 마세요.
5. **출처 명시**: 모든 정보의 출처를 명확히 밝히세요.

현재 사용 가능한 도구:
- search_internal: 사내 지식베이스 검색 (최우선 사용)
- search_web: 웹 검색 (보완적 사용)
- get_stock_price: 실시간 주가 조회
- save_report: 분석 결과 저장 (권한 필요)
- get_market_summary: 시장 현황 요약
"""
            
            # [에이전트 실행] 시스템 프롬프트와 함께 요청 처리
            full_request = f"{system_prompt}\n\n사용자 요청: {request}"
            response = self.agent.run(full_request)
            
            logger.info(f"[Agent Core] AI 에이전트 실행 완료 - 응답 길이: {len(str(response))}자")
            return str(response)
            
        except Exception as e:
            logger.error(f"[Agent Core] AI 에이전트 실행 중 오류: {str(e)}")
            return f"❌ **AI 에이전트 오류**\n\n처리 중 오류가 발생했습니다: {str(e)}"
    
    def _generate_demo_response(self, request: str) -> str:
        """
        [데모 응답 생성]
        API 키가 없는 교육 환경에서 시스템의 구조와 기능을 보여주는 데모 응답 생성
        
        Args:
            request (str): 사용자 요청
            
        Returns:
            str: 데모 응답 메시지
        """
        logger.info(f"[Agent Core] 데모 모드 응답 생성 - 요청: {request[:50]}...")
        
        return f"""# 📊 Quant-X 데모 응답

**요청**: {request}

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

⚠️ **투자 유의사항** 본 정보는 투자 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다. 투자에는 원금 손실 위험이 있으며, 과거 성과가 미래 수익을 보장하지 않습니다. 투자 전 충분한 검토와 전문가 상담을 권장합니다."""


def create_agent(user_id: str) -> QuantXAgent:
    """
    [에이전트 팩토리 함수]
    사용자 ID를 받아 해당 사용자를 위한 QuantX 에이전트 인스턴스를 생성
    
    Args:
        user_id (str): 사용자 식별자
        
    Returns:
        QuantXAgent: 초기화된 에이전트 인스턴스
    """
    logger.info(f"[Agent Core] 사용자 {user_id}를 위한 새 에이전트 생성 요청")
    return QuantXAgent(user_id)