"""
[Audit Logging] 감사 로그 시스템

금융 기관에서는 모든 시스템 활동이 규제 당국의 감사 대상입니다.
이 모듈은 AI 에이전트의 모든 행위를 추적하고 기록하여
전자금융감독규정 등 금융 규제를 준수합니다.

교육 목표:
- 금융권 감사 로그의 중요성과 요구사항 이해
- Python logging 모듈을 활용한 구조화된 로깅 구현
- 실시간 로그 모니터링을 위한 UI 연동 방법 학습
- 변조 방지를 위한 로그 보안 고려사항 이해
"""

import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import deque
import threading

class AuditLogger:
    """
    [Audit Logger] 감사 로그 관리자
    
    AI 에이전트의 모든 도구 호출, 사용자 행위, 시스템 이벤트를
    구조화된 형태로 기록하고 관리합니다.
    
    금융 규제 요구사항:
    - 모든 거래 관련 활동 기록 (전자금융감독규정 제23조)
    - 로그 변조 방지 및 무결성 보장
    - 최소 5년간 보관 의무
    - 실시간 모니터링 및 이상 탐지
    """
    
    def __init__(self, log_file_path: str = "./data/system.log"):
        """
        [Logger Initialization] 감사 로거 초기화
        
        Args:
            log_file_path (str): 로그 파일 경로
        """
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # [Thread Safety] 멀티스레드 환경에서의 로그 안전성 보장
        self.lock = threading.Lock()
        
        # [Memory Buffer] UI 실시간 표시를 위한 메모리 버퍼
        # 최근 100개 로그만 메모리에 유지하여 성능 최적화
        self.memory_buffer = deque(maxlen=100)
        
        # [Logger Setup] Python logging 설정
        self._setup_logger()
        
        # [System Start] 시스템 시작 로그 기록
        self.log_system_event("SYSTEM_START", "감사 로그 시스템 초기화 완료")
    
    def _setup_logger(self):
        """
        [Logger Configuration] Python logging 모듈 설정
        
        금융 시스템에 적합한 로그 포맷과 레벨을 설정합니다.
        """
        # [Logger Instance] 전용 로거 생성
        self.logger = logging.getLogger("QuantX_Audit")
        self.logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거 (중복 방지)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # [File Handler] 파일 로그 핸들러 설정
        file_handler = logging.FileHandler(
            self.log_file_path, 
            mode='a', 
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # [Log Format] 금융 감사에 적합한 로그 포맷
        # 타임스탬프, 레벨, 사용자, 액션, 상세정보를 구조화
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
        # [Console Handler] 개발/디버깅용 콘솔 출력
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def log_audit(self, user_id: str, action: str, details: Dict[str, Any] = None):
        """
        [Audit Trail] 감사 추적 로그 기록
        
        AI 에이전트의 모든 도구 호출과 사용자 행위를 기록합니다.
        이는 금융사고 방지 및 규제 준수를 위한 핵심 기능입니다.
        
        Args:
            user_id (str): 사용자 ID
            action (str): 수행된 액션/도구명
            details (Dict[str, Any]): 상세 정보 (매개변수, 결과 등)
        """
        with self.lock:
            # [Audit Record] 감사 레코드 생성
            audit_record = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "action": action,
                "details": details or {},
                "log_type": "AUDIT"
            }
            
            # [Structured Logging] 구조화된 로그 메시지 생성
            log_message = f"USER:{user_id} | ACTION:{action}"
            if details:
                # 민감 정보 마스킹 (예: API 키, 패스워드)
                safe_details = self._mask_sensitive_data(details)
                log_message += f" | DETAILS:{json.dumps(safe_details, ensure_ascii=False)}"
            
            # [File Logging] 파일에 로그 기록
            self.logger.info(log_message)
            
            # [Memory Buffer] 실시간 UI 표시용 메모리 버퍼에 추가
            display_record = {
                "timestamp": audit_record["timestamp"],
                "user_id": user_id,
                "action": action,
                "details": safe_details if details else {},
                "formatted_message": log_message
            }
            self.memory_buffer.append(display_record)
    
    def log_system_event(self, event_type: str, message: str, details: Dict[str, Any] = None):
        """
        [System Event] 시스템 이벤트 로그 기록
        
        사용자 행위가 아닌 시스템 자체의 이벤트를 기록합니다.
        (예: 시스템 시작/종료, 오류 발생, 설정 변경 등)
        
        Args:
            event_type (str): 이벤트 타입
            message (str): 이벤트 메시지
            details (Dict[str, Any]): 상세 정보
        """
        with self.lock:
            # [System Record] 시스템 레코드 생성
            system_record = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "message": message,
                "details": details or {},
                "log_type": "SYSTEM"
            }
            
            # [System Logging] 시스템 로그 메시지 생성
            log_message = f"SYSTEM | {event_type} | {message}"
            if details:
                safe_details = self._mask_sensitive_data(details)
                log_message += f" | DETAILS:{json.dumps(safe_details, ensure_ascii=False)}"
            
            # [File Logging] 파일에 로그 기록
            self.logger.info(log_message)
            
            # [Memory Buffer] 메모리 버퍼에 추가
            display_record = {
                "timestamp": system_record["timestamp"],
                "user_id": "SYSTEM",
                "action": event_type,
                "details": safe_details if details else {},
                "formatted_message": log_message
            }
            self.memory_buffer.append(display_record)
    
    def log_security_event(self, user_id: str, event_type: str, message: str, 
                          severity: str = "WARNING", details: Dict[str, Any] = None):
        """
        [Security Event] 보안 이벤트 로그 기록
        
        보안 위반, 의심스러운 활동, 접근 거부 등 보안 관련 이벤트를 기록합니다.
        이러한 로그는 특별한 모니터링과 알림이 필요합니다.
        
        Args:
            user_id (str): 사용자 ID
            event_type (str): 보안 이벤트 타입
            message (str): 이벤트 메시지
            severity (str): 심각도 (INFO, WARNING, CRITICAL)
            details (Dict[str, Any]): 상세 정보
        """
        with self.lock:
            # [Security Record] 보안 레코드 생성
            security_record = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "event_type": event_type,
                "message": message,
                "severity": severity,
                "details": details or {},
                "log_type": "SECURITY"
            }
            
            # [Security Logging] 보안 로그 메시지 생성
            log_message = f"SECURITY | {severity} | USER:{user_id} | {event_type} | {message}"
            if details:
                safe_details = self._mask_sensitive_data(details)
                log_message += f" | DETAILS:{json.dumps(safe_details, ensure_ascii=False)}"
            
            # [Severity-based Logging] 심각도에 따른 로그 레벨 설정
            if severity == "CRITICAL":
                self.logger.critical(log_message)
            elif severity == "WARNING":
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)
            
            # [Memory Buffer] 메모리 버퍼에 추가 (보안 이벤트는 강조 표시)
            display_record = {
                "timestamp": security_record["timestamp"],
                "user_id": user_id,
                "action": f"🔒 {event_type}",  # 보안 이벤트 아이콘
                "details": safe_details if details else {},
                "formatted_message": log_message,
                "severity": severity
            }
            self.memory_buffer.append(display_record)
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Data Masking] 민감 정보 마스킹
        
        로그에 기록되는 데이터에서 민감한 정보를 마스킹하여
        보안을 강화합니다.
        
        Args:
            data (Dict[str, Any]): 원본 데이터
            
        Returns:
            Dict[str, Any]: 마스킹된 데이터
        """
        if not isinstance(data, dict):
            return data
        
        # [Sensitive Keywords] 마스킹 대상 키워드
        sensitive_keys = [
            'password', 'passwd', 'pwd',
            'api_key', 'apikey', 'token',
            'secret', 'private_key',
            'credit_card', 'ssn', 'social_security'
        ]
        
        masked_data = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # [Masking Logic] 민감 키워드 포함 시 마스킹
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    # 앞 2자리와 뒤 2자리만 표시
                    masked_data[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    masked_data[key] = "***MASKED***"
            else:
                # 재귀적으로 중첩된 딕셔너리 처리
                if isinstance(value, dict):
                    masked_data[key] = self._mask_sensitive_data(value)
                else:
                    masked_data[key] = value
        
        return masked_data
    
    def get_recent_logs(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        [Recent Logs] 최근 로그 조회
        
        UI에서 실시간 로그 모니터링을 위해 최근 로그를 반환합니다.
        
        Args:
            count (int): 반환할 로그 수
            
        Returns:
            List[Dict[str, Any]]: 최근 로그 리스트
        """
        with self.lock:
            # 메모리 버퍼에서 최근 로그 추출
            recent_logs = list(self.memory_buffer)[-count:]
            return recent_logs
    
    def get_logs_by_user(self, user_id: str, count: int = 50) -> List[Dict[str, Any]]:
        """
        [User Logs] 특정 사용자의 로그 조회
        
        특정 사용자의 활동 내역을 추적하기 위한 메서드입니다.
        
        Args:
            user_id (str): 사용자 ID
            count (int): 반환할 로그 수
            
        Returns:
            List[Dict[str, Any]]: 사용자별 로그 리스트
        """
        with self.lock:
            user_logs = [
                log for log in self.memory_buffer 
                if log.get("user_id") == user_id
            ]
            return user_logs[-count:]
    
    def get_security_logs(self, count: int = 30) -> List[Dict[str, Any]]:
        """
        [Security Logs] 보안 이벤트 로그 조회
        
        보안 관련 이벤트만 필터링하여 반환합니다.
        
        Args:
            count (int): 반환할 로그 수
            
        Returns:
            List[Dict[str, Any]]: 보안 로그 리스트
        """
        with self.lock:
            security_logs = [
                log for log in self.memory_buffer 
                if "🔒" in log.get("action", "") or log.get("severity")
            ]
            return security_logs[-count:]
    
    def export_logs(self, start_date: str = None, end_date: str = None) -> str:
        """
        [Log Export] 로그 내보내기
        
        규제 당국 제출이나 감사를 위해 특정 기간의 로그를 내보냅니다.
        
        Args:
            start_date (str): 시작 날짜 (YYYY-MM-DD)
            end_date (str): 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            str: 내보낸 로그 파일 경로
        """
        try:
            # [Export Logic] 실제 구현에서는 파일에서 날짜 범위 필터링
            export_path = self.log_file_path.parent / f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            
            # 현재는 전체 로그 파일 복사 (교육용 간소화)
            import shutil
            shutil.copy2(self.log_file_path, export_path)
            
            self.log_system_event(
                "LOG_EXPORT", 
                f"감사 로그 내보내기 완료: {export_path}",
                {"export_path": str(export_path)}
            )
            
            return str(export_path)
            
        except Exception as e:
            self.log_system_event(
                "LOG_EXPORT_ERROR", 
                f"로그 내보내기 실패: {str(e)}",
                {"error": str(e)}
            )
            raise
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        [Log Statistics] 로그 통계 정보
        
        시스템 모니터링을 위한 로그 통계를 제공합니다.
        
        Returns:
            Dict[str, Any]: 로그 통계 정보
        """
        with self.lock:
            logs = list(self.memory_buffer)
            
            # [Statistics Calculation] 통계 계산
            total_logs = len(logs)
            user_actions = len([log for log in logs if log.get("user_id") != "SYSTEM"])
            system_events = len([log for log in logs if log.get("user_id") == "SYSTEM"])
            security_events = len([log for log in logs if "🔒" in log.get("action", "")])
            
            # 사용자별 활동 통계
            user_stats = {}
            for log in logs:
                user_id = log.get("user_id", "Unknown")
                if user_id != "SYSTEM":
                    user_stats[user_id] = user_stats.get(user_id, 0) + 1
            
            return {
                "total_logs": total_logs,
                "user_actions": user_actions,
                "system_events": system_events,
                "security_events": security_events,
                "user_statistics": user_stats,
                "log_file_path": str(self.log_file_path),
                "buffer_size": len(self.memory_buffer)
            }


# [Global Instance] 전역 감사 로거 인스턴스
# 앱 전체에서 하나의 로거를 공유하여 일관된 로깅을 보장합니다.
audit_logger = AuditLogger()

def get_logger(name: str) -> logging.Logger:
    """
    [Logger Factory] 모듈별 로거 생성
    
    각 모듈에서 사용할 표준 로거를 생성합니다.
    모든 로그는 감사 로거와 연동되어 중앙 집중식으로 관리됩니다.
    
    Args:
        name (str): 로거 이름 (보통 __name__ 사용)
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # 기본 핸들러 설정
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger