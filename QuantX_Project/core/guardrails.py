"""
[Security Guardrails] 보안 가드레일 시스템

금융 AI 에이전트는 악의적인 입력이나 부적절한 출력으로부터 
시스템을 보호해야 합니다. 이 모듈은 입력 검증과 출력 필터링을 
통해 금융 규제 준수와 보안을 강화합니다.

교육 목표:
- 금융권 AI의 보안 위험 요소 이해
- 입력 검증(Input Validation) 패턴 학습
- 출력 필터링(Output Filtering) 구현
- 불완전 판매 방지 및 규제 준수 메커니즘 이해
- OpenAI Moderation API를 활용한 고급 콘텐츠 필터링 시스템 구현
- 다층 보안 아키텍처(키워드 + AI 모더레이션) 설계 패턴 학습
"""

import re
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

# [OpenAI Integration] OpenAI Moderation API 연동
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class RiskLevel(Enum):
    """
    [Risk Level] 위험도 분류
    
    입력이나 출력의 위험도를 분류하여 적절한 대응을 수행합니다.
    """
    SAFE = "safe"           # 안전: 통과
    WARNING = "warning"     # 경고: 주의 메시지와 함께 통과
    BLOCKED = "blocked"     # 차단: 처리 거부

@dataclass
class ModerationResult:
    """
    [Moderation Result] OpenAI Moderation API 결과
    
    OpenAI Moderation API의 응답을 구조화한 데이터 클래스입니다.
    """
    flagged: bool
    categories: Dict[str, bool]
    category_scores: Dict[str, float]
    error: Optional[str] = None

@dataclass
class GuardrailResult:
    """
    [Guardrail Result] 가드레일 검사 결과
    
    입력/출력 검사 결과와 관련 정보를 담는 데이터 클래스입니다.
    키워드 필터링과 AI 모더레이션 결과를 모두 포함합니다.
    """
    is_safe: bool
    risk_level: RiskLevel
    message: str
    detected_issues: List[str]
    filtered_content: Optional[str] = None
    moderation_result: Optional[ModerationResult] = None
    security_layers: List[str] = None  # 적용된 보안 계층 목록

class SecurityGuardrails:
    """
    [Security Guardrails] 보안 가드레일 관리자
    
    AI 에이전트의 입력과 출력을 검사하여 보안 위험을 방지하고
    금융 규제를 준수하도록 보장합니다.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # [OpenAI Moderation] OpenAI Moderation API 클라이언트 초기화
        self.openai_client = None
        self.moderation_enabled = False
        
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key and api_key != 'your_openai_api_key_here':
                try:
                    self.openai_client = OpenAI(api_key=api_key)
                    self.moderation_enabled = True
                    self.logger.info("[Guardrails] OpenAI Moderation API 활성화됨")
                except Exception as e:
                    self.logger.warning(f"[Guardrails] OpenAI 클라이언트 초기화 실패: {e}")
            else:
                self.logger.info("[Guardrails] OpenAI API 키가 설정되지 않음. 키워드 필터링만 사용")
        else:
            self.logger.warning("[Guardrails] OpenAI 라이브러리를 찾을 수 없음. 키워드 필터링만 사용")
        
        # [Moderation Thresholds] AI 모더레이션 임계값 설정
        # 각 카테고리별로 차단 임계값을 설정합니다 (0.0 ~ 1.0)
        self.moderation_thresholds = {
            'hate': 0.3,           # 혐오 발언
            'hate/threatening': 0.2, # 위협적 혐오 발언
            'harassment': 0.4,     # 괴롭힘
            'harassment/threatening': 0.2, # 위협적 괴롭힘
            'self-harm': 0.3,      # 자해
            'self-harm/intent': 0.2, # 자해 의도
            'self-harm/instructions': 0.2, # 자해 지시
            'sexual': 0.5,         # 성적 콘텐츠
            'sexual/minors': 0.1,  # 미성년자 성적 콘텐츠 (매우 엄격)
            'violence': 0.4,       # 폭력
            'violence/graphic': 0.3 # 그래픽 폭력
        }
        
        # [Input Blacklist] 입력 차단 키워드
        # 금융 시스템 보안과 관련된 위험 키워드들
        self.input_blacklist = [
            # 보안 위협 관련
            "해킹", "크래킹", "피싱", "스미싱",
            "sql injection", "xss", "csrf",
            
            # 내부자 거래 관련
            "내부자", "내부정보", "미공개정보",
            "인사이더", "insider trading",
            
            # 시장 조작 관련
            "작전주", "작전세력", "주가조작",
            "펌프앤덤프", "pump and dump",
            
            # 불법 정보 관련
            "찌라시", "루머", "가짜뉴스",
            "미확인정보", "카더라"
        ]
        
        # [Output Compliance] 출력 규제 준수 키워드
        # 불완전 판매 방지를 위한 금지 표현들
        self.compliance_violations = [
            # 확실성 표현 (불완전 판매 금지)
            "무조건", "확실한", "보장", "100%",
            "반드시", "틀림없이", "확실히",
            
            # 투자 권유 표현
            "사세요", "파세요", "매수하세요", "매도하세요",
            "추천합니다", "강력추천",
            
            # 수익 보장 표현
            "수익보장", "원금보장", "손실없음",
            "위험없음", "안전한투자"
        ]
        
        # [Compliance Replacements] 규제 준수 대체 표현
        self.compliance_replacements = {
            "무조건": "[검열됨 - 불확실성 표현 필요]",
            "확실한": "가능성이 높은",
            "보장": "예상",
            "100%": "높은 확률로",
            "반드시": "일반적으로",
            "틀림없이": "추정되는",
            "확실히": "예상되는",
            "사세요": "매수를 고려해볼 수 있습니다",
            "파세요": "매도를 검토해볼 수 있습니다",
            "추천합니다": "참고하시기 바랍니다",
            "수익보장": "[검열됨 - 수익 보장 불가]",
            "원금보장": "[검열됨 - 원금 보장 불가]"
        }
        
        # [Pattern Matching] 정규표현식 패턴
        self.suspicious_patterns = [
            r'API[_\s]*KEY[_\s]*[=:]\s*["\']?[\w\-]{10,}',  # API 키 패턴
            r'password[_\s]*[=:]\s*["\']?[\w]{6,}',          # 패스워드 패턴
            r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',      # 신용카드 번호 패턴
            r'\d{6}[-\s]?\d{7}',                             # 주민등록번호 패턴
        ]
    
    def _call_openai_moderation(self, text: str) -> ModerationResult:
        """
        [OpenAI Moderation] OpenAI Moderation API 호출
        
        OpenAI의 Moderation API를 사용하여 텍스트의 안전성을 검사합니다.
        이는 키워드 필터링보다 더 정교한 AI 기반 콘텐츠 분석을 제공합니다.
        
        Args:
            text (str): 검사할 텍스트
            
        Returns:
            ModerationResult: 모더레이션 결과
        """
        if not self.moderation_enabled or not self.openai_client:
            return ModerationResult(
                flagged=False,
                categories={},
                category_scores={},
                error="OpenAI Moderation API 사용 불가"
            )
        
        try:
            # [API Call] OpenAI Moderation API 호출
            response = self.openai_client.moderations.create(input=text)
            result = response.results[0]
            
            # [Result Processing] 결과 처리
            moderation_result = ModerationResult(
                flagged=result.flagged,
                categories=dict(result.categories),
                category_scores=dict(result.category_scores)
            )
            
            # [Threshold Check] 사용자 정의 임계값 검사
            # OpenAI의 기본 판정보다 더 엄격한 기준을 적용할 수 있습니다
            custom_flagged = False
            for category, score in moderation_result.category_scores.items():
                threshold = self.moderation_thresholds.get(category, 0.5)
                if score > threshold:
                    custom_flagged = True
                    self.logger.warning(
                        f"[Moderation] 임계값 초과 - {category}: {score:.3f} > {threshold}"
                    )
            
            # 사용자 정의 임계값이 더 엄격한 경우 적용
            if custom_flagged and not moderation_result.flagged:
                moderation_result.flagged = True
                self.logger.info("[Moderation] 사용자 정의 임계값에 의해 차단됨")
            
            return moderation_result
            
        except Exception as e:
            self.logger.error(f"[Moderation] OpenAI Moderation API 호출 실패: {e}")
            return ModerationResult(
                flagged=False,
                categories={},
                category_scores={},
                error=str(e)
            )
    
    def check_input(self, user_input: str, user_id: str = "unknown") -> GuardrailResult:
        """
        [Input Validation] 2단계 입력 검증 시스템
        
        1단계: 키워드 기반 빠른 필터링 (Rule-based)
        2단계: OpenAI Moderation API 기반 AI 분석 (AI-based)
        
        이 다층 보안 구조는 실제 금융권에서 사용되는 엔터프라이즈급 
        보안 시스템의 패턴을 교육 목적으로 구현한 것입니다.
        
        Args:
            user_input (str): 사용자 입력 텍스트
            user_id (str): 사용자 ID (로깅용)
            
        Returns:
            GuardrailResult: 종합 검증 결과
        """
        detected_issues = []
        risk_level = RiskLevel.SAFE
        security_layers = []
        moderation_result = None
        
        # ==================== 1단계: 키워드 기반 필터링 ====================
        self.logger.info(f"[Guardrails] 1단계 검사 시작 - 사용자: {user_id}")
        security_layers.append("키워드 필터링")
        
        # [Blacklist Check] 차단 키워드 검사
        input_lower = user_input.lower()
        for keyword in self.input_blacklist:
            if keyword in input_lower:
                detected_issues.append(f"차단 키워드 감지: {keyword}")
                risk_level = RiskLevel.BLOCKED
                self.logger.warning(f"[Guardrails] 키워드 차단: {keyword}")
        
        # [Pattern Check] 의심스러운 패턴 검사
        for pattern in self.suspicious_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                detected_issues.append("민감 정보 패턴 감지")
                risk_level = RiskLevel.BLOCKED
                self.logger.warning("[Guardrails] 민감 정보 패턴 감지")
        
        # [Length Check] 입력 길이 검사 (DoS 방지)
        if len(user_input) > 10000:
            detected_issues.append("입력 길이 초과 (10,000자 제한)")
            risk_level = RiskLevel.BLOCKED
            self.logger.warning(f"[Guardrails] 입력 길이 초과: {len(user_input)}자")
        
        # [Special Character Check] 특수 문자 남용 검사
        special_char_ratio = len(re.findall(r'[^\w\s가-힣]', user_input)) / len(user_input) if user_input else 0
        if special_char_ratio > 0.3:
            detected_issues.append("특수 문자 비율 과다")
            if risk_level == RiskLevel.SAFE:  # 기존 차단 사유가 없는 경우만
                risk_level = RiskLevel.WARNING
        
        # ==================== 2단계: AI 모더레이션 ====================
        # 1단계에서 차단되지 않은 경우에만 AI 모더레이션 수행
        if risk_level != RiskLevel.BLOCKED and len(user_input.strip()) > 0:
            self.logger.info(f"[Guardrails] 2단계 검사 시작 - OpenAI Moderation")
            security_layers.append("AI 모더레이션")
            
            moderation_result = self._call_openai_moderation(user_input)
            
            if moderation_result.flagged:
                # AI 모더레이션에서 위험 콘텐츠로 판정된 경우
                risk_level = RiskLevel.BLOCKED
                
                # 구체적인 위험 카테고리 정보 추가
                flagged_categories = [
                    category for category, is_flagged in moderation_result.categories.items() 
                    if is_flagged
                ]
                
                if flagged_categories:
                    detected_issues.append(f"AI 모더레이션 차단: {', '.join(flagged_categories)}")
                else:
                    detected_issues.append("AI 모더레이션에 의해 부적절한 콘텐츠로 판정됨")
                
                self.logger.warning(f"[Guardrails] AI 모더레이션 차단: {flagged_categories}")
            
            elif moderation_result.error:
                # AI 모더레이션 API 호출 실패 시 경고 처리
                detected_issues.append(f"AI 모더레이션 오류: {moderation_result.error}")
                if risk_level == RiskLevel.SAFE:
                    risk_level = RiskLevel.WARNING
                self.logger.warning(f"[Guardrails] AI 모더레이션 오류: {moderation_result.error}")
        
        # ==================== 결과 생성 및 로깅 ====================
        is_safe = risk_level != RiskLevel.BLOCKED
        
        if risk_level == RiskLevel.BLOCKED:
            message = "입력이 보안 정책에 위배되어 차단되었습니다."
            # [Security Logging] 보안 이벤트 로깅
            from .logger import audit_logger
            audit_logger.log_security_event(
                user_id=user_id,
                event_type="INPUT_BLOCKED",
                message="위험한 입력 차단",
                severity="WARNING",
                details={
                    "input_length": len(user_input),
                    "detected_issues": detected_issues,
                    "security_layers": security_layers,
                    "moderation_flagged": moderation_result.flagged if moderation_result else False,
                    "input_preview": user_input[:100] + "..." if len(user_input) > 100 else user_input
                }
            )
        elif risk_level == RiskLevel.WARNING:
            message = "입력에 주의가 필요한 내용이 포함되어 있습니다."
        else:
            message = "입력이 안전합니다."
            self.logger.info(f"[Guardrails] 입력 검증 통과 - 사용자: {user_id}, 보안 계층: {security_layers}")
        
        return GuardrailResult(
            is_safe=is_safe,
            risk_level=risk_level,
            message=message,
            detected_issues=detected_issues,
            moderation_result=moderation_result,
            security_layers=security_layers
        )
    
    def filter_output(self, output: str, user_id: str = "unknown") -> GuardrailResult:
        """
        [Output Filtering] 2단계 출력 필터링 시스템
        
        1단계: 규제 준수 및 키워드 기반 필터링 (Compliance-based)
        2단계: OpenAI Moderation API 기반 AI 분석 (AI-based)
        
        AI 에이전트의 출력을 검사하여 불완전 판매 방지, 규제 준수, 
        그리고 부적절한 콘텐츠 차단을 보장합니다.
        
        Args:
            output (str): AI 에이전트 출력 텍스트
            user_id (str): 사용자 ID (로깅용)
            
        Returns:
            GuardrailResult: 종합 필터링 결과
        """
        detected_issues = []
        filtered_content = output
        risk_level = RiskLevel.SAFE
        security_layers = []
        moderation_result = None
        
        # ==================== 1단계: 규제 준수 필터링 ====================
        self.logger.info(f"[Guardrails] 출력 필터링 1단계 시작 - 사용자: {user_id}")
        security_layers.append("규제 준수 필터링")
        
        # [Compliance Check] 규제 준수 검사
        for violation in self.compliance_violations:
            if violation in output:
                detected_issues.append(f"규제 위반 표현: {violation}")
                risk_level = RiskLevel.WARNING
                
                # [Content Replacement] 위반 표현 대체
                if violation in self.compliance_replacements:
                    replacement = self.compliance_replacements[violation]
                    filtered_content = filtered_content.replace(violation, replacement)
                    self.logger.info(f"[Output Filter] '{violation}' -> '{replacement}' 대체")
        
        # [Disclaimer Addition] 면책 조항 추가
        if self._needs_disclaimer(filtered_content):
            disclaimer = self._get_financial_disclaimer()
            filtered_content += f"\n\n{disclaimer}"
            detected_issues.append("금융 면책 조항 추가")
        
        # [Sensitive Data Check] 민감 데이터 노출 검사
        for pattern in self.suspicious_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                detected_issues.append("민감 정보 노출 위험")
                risk_level = RiskLevel.BLOCKED
                filtered_content = re.sub(pattern, "[민감정보 차단]", filtered_content, flags=re.IGNORECASE)
        
        # ==================== 2단계: AI 모더레이션 ====================
        # 1단계에서 차단되지 않은 경우에만 AI 모더레이션 수행
        if risk_level != RiskLevel.BLOCKED and len(filtered_content.strip()) > 0:
            self.logger.info(f"[Guardrails] 출력 필터링 2단계 시작 - OpenAI Moderation")
            security_layers.append("AI 모더레이션")
            
            moderation_result = self._call_openai_moderation(filtered_content)
            
            if moderation_result.flagged:
                # AI 모더레이션에서 위험 콘텐츠로 판정된 경우
                risk_level = RiskLevel.BLOCKED
                
                # 구체적인 위험 카테고리 정보 추가
                flagged_categories = [
                    category for category, is_flagged in moderation_result.categories.items() 
                    if is_flagged
                ]
                
                if flagged_categories:
                    detected_issues.append(f"AI 모더레이션 차단: {', '.join(flagged_categories)}")
                else:
                    detected_issues.append("AI 모더레이션에 의해 부적절한 출력으로 판정됨")
                
                # 출력 내용을 안전한 메시지로 대체
                filtered_content = "[콘텐츠 차단] 해당 응답은 보안 정책에 위배되어 표시할 수 없습니다."
                
                self.logger.warning(f"[Guardrails] 출력 AI 모더레이션 차단: {flagged_categories}")
            
            elif moderation_result.error:
                # AI 모더레이션 API 호출 실패 시 경고 처리
                detected_issues.append(f"AI 모더레이션 오류: {moderation_result.error}")
                if risk_level == RiskLevel.SAFE:
                    risk_level = RiskLevel.WARNING
                self.logger.warning(f"[Guardrails] 출력 AI 모더레이션 오류: {moderation_result.error}")
        
        # ==================== 결과 생성 및 로깅 ====================
        is_safe = risk_level != RiskLevel.BLOCKED
        
        if risk_level == RiskLevel.BLOCKED:
            message = "출력이 보안 정책에 위배되어 차단되었습니다."
            # [Security Logging] 보안 이벤트 로깅
            from .logger import audit_logger
            audit_logger.log_security_event(
                user_id=user_id,
                event_type="OUTPUT_BLOCKED",
                message="위험한 출력 차단",
                severity="CRITICAL",
                details={
                    "output_length": len(output),
                    "detected_issues": detected_issues,
                    "security_layers": security_layers,
                    "moderation_flagged": moderation_result.flagged if moderation_result else False
                }
            )
        elif risk_level == RiskLevel.WARNING:
            message = "출력이 규제 준수를 위해 수정되었습니다."
            # [Compliance Logging] 규제 준수 로깅
            from .logger import audit_logger
            audit_logger.log_audit(
                user_id=user_id,
                action="OUTPUT_FILTERED",
                details={
                    "detected_issues": detected_issues,
                    "modifications_made": len(detected_issues)
                }
            )
        else:
            message = "출력이 안전합니다."
            self.logger.info(f"[Guardrails] 출력 필터링 통과 - 사용자: {user_id}, 보안 계층: {security_layers}")
        
        return GuardrailResult(
            is_safe=is_safe,
            risk_level=risk_level,
            message=message,
            detected_issues=detected_issues,
            filtered_content=filtered_content,
            moderation_result=moderation_result,
            security_layers=security_layers
        )
    
    def _needs_disclaimer(self, content: str) -> bool:
        """
        [Disclaimer Check] 면책 조항 필요성 검사
        
        금융 관련 내용에 면책 조항이 필요한지 판단합니다.
        
        Args:
            content (str): 검사할 내용
            
        Returns:
            bool: 면책 조항 필요 여부
        """
        financial_keywords = [
            "투자", "주식", "채권", "펀드", "수익",
            "손실", "위험", "매수", "매도", "추천",
            "전망", "예상", "분석", "평가"
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in financial_keywords)
    
    def _get_financial_disclaimer(self) -> str:
        """
        [Financial Disclaimer] 금융 면책 조항 생성
        
        Returns:
            str: 금융 면책 조항 텍스트
        """
        return (
            "⚠️ **투자 유의사항**\n"
            "본 정보는 투자 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다. "
            "투자에는 원금 손실 위험이 있으며, 과거 성과가 미래 수익을 보장하지 않습니다. "
            "투자 전 충분한 검토와 전문가 상담을 권장합니다."
        )
    
    def check_compliance_score(self, content: str) -> Dict[str, Any]:
        """
        [Compliance Score] 규제 준수 점수 계산
        
        콘텐츠의 규제 준수 수준을 점수로 평가합니다.
        
        Args:
            content (str): 평가할 내용
            
        Returns:
            Dict[str, Any]: 준수 점수 및 상세 정보
        """
        total_violations = 0
        violation_details = []
        
        # 규제 위반 표현 검사
        for violation in self.compliance_violations:
            count = content.lower().count(violation)
            if count > 0:
                total_violations += count
                violation_details.append({
                    "violation": violation,
                    "count": count,
                    "severity": "high" if violation in ["무조건", "보장", "100%"] else "medium"
                })
        
        # 점수 계산 (100점 만점)
        max_violations = 10  # 최대 위반 기준
        score = max(0, 100 - (total_violations * 100 / max_violations))
        
        # 등급 결정
        if score >= 90:
            grade = "A"
            status = "우수"
        elif score >= 80:
            grade = "B"
            status = "양호"
        elif score >= 70:
            grade = "C"
            status = "보통"
        elif score >= 60:
            grade = "D"
            status = "주의"
        else:
            grade = "F"
            status = "위험"
        
        return {
            "score": round(score, 1),
            "grade": grade,
            "status": status,
            "total_violations": total_violations,
            "violation_details": violation_details,
            "recommendations": self._get_compliance_recommendations(violation_details)
        }
    
    def _get_compliance_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """
        [Compliance Recommendations] 규제 준수 개선 권장사항
        
        Args:
            violations (List[Dict[str, Any]]): 위반 내역
            
        Returns:
            List[str]: 개선 권장사항
        """
        recommendations = []
        
        high_severity_violations = [v for v in violations if v["severity"] == "high"]
        if high_severity_violations:
            recommendations.append("확실성을 나타내는 표현을 '가능성', '예상' 등으로 수정하세요.")
        
        investment_violations = [v for v in violations if any(word in v["violation"] for word in ["사세요", "파세요", "추천"])]
        if investment_violations:
            recommendations.append("직접적인 투자 권유 대신 '참고용 정보' 형태로 제공하세요.")
        
        guarantee_violations = [v for v in violations if any(word in v["violation"] for word in ["보장", "확실"])]
        if guarantee_violations:
            recommendations.append("수익이나 결과를 보장하는 표현을 제거하고 위험성을 명시하세요.")
        
        if not recommendations:
            recommendations.append("현재 규제 준수 수준이 양호합니다.")
        
        return recommendations
    
    def get_security_report(self) -> Dict[str, Any]:
        """
        [Security Report] 고급 보안 현황 리포트
        
        키워드 필터링과 OpenAI Moderation을 포함한 
        다층 보안 시스템의 상태와 통계를 제공합니다.
        
        Returns:
            Dict[str, Any]: 종합 보안 리포트
        """
        # [Security Layers] 보안 계층 정보
        security_layers = {
            "keyword_filtering": {
                "status": "활성",
                "blacklist_size": len(self.input_blacklist),
                "pattern_rules": len(self.suspicious_patterns),
                "compliance_rules": len(self.compliance_violations)
            },
            "ai_moderation": {
                "status": "활성" if self.moderation_enabled else "비활성",
                "provider": "OpenAI" if self.moderation_enabled else "없음",
                "api_available": self.openai_client is not None,
                "custom_thresholds": len(self.moderation_thresholds),
                "categories_monitored": list(self.moderation_thresholds.keys()) if self.moderation_enabled else []
            }
        }
        
        # [Overall Security Level] 전체 보안 수준 평가
        if self.moderation_enabled:
            security_level = "최고"
            security_score = 95
            active_layers = ["키워드 필터링", "AI 모더레이션"]
        else:
            security_level = "높음"
            security_score = 75
            active_layers = ["키워드 필터링"]
        
        # [Recommendations] 보안 강화 권장사항
        recommendations = []
        if not self.moderation_enabled:
            recommendations.append("OpenAI API 키를 설정하여 AI 모더레이션 기능을 활성화하세요")
        
        recommendations.extend([
            "정기적인 키워드 업데이트 필요",
            "새로운 위협 패턴 모니터링 강화",
            "사용자 교육 및 가이드라인 배포",
            "모더레이션 임계값 정기 검토"
        ])
        
        return {
            "guardrail_status": "활성",
            "security_level": security_level,
            "security_score": security_score,
            "active_layers": active_layers,
            "security_layers": security_layers,
            "last_updated": "2024-12-04",
            "recommendations": recommendations,
            "system_info": {
                "openai_available": OPENAI_AVAILABLE,
                "moderation_enabled": self.moderation_enabled,
                "total_rules": len(self.input_blacklist) + len(self.compliance_violations) + len(self.suspicious_patterns)
            }
        }


# [Global Instance] 전역 보안 가드레일 인스턴스
# 앱 전체에서 일관된 보안 정책을 적용합니다.
security_guardrails = SecurityGuardrails()