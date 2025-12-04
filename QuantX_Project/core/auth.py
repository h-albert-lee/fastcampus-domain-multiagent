"""
[Authentication & Authorization] 사용자 인증 및 권한 관리 시스템

금융 엔터프라이즈에서는 엄격한 접근 제어가 필수입니다. 
이 모듈은 Role-Based Access Control (RBAC)을 구현하여
사용자의 역할에 따라 AI 에이전트의 기능을 제한합니다.

교육 목표:
- 금융권의 계층적 권한 구조 이해
- RBAC 패턴을 통한 보안 설계 학습
- 에이전트 도구별 권한 제어 메커니즘 구현
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

class UserRole(Enum):
    """
    [Role Definition] 사용자 역할 정의
    
    금융 기관의 일반적인 계층 구조를 반영한 역할 체계입니다.
    각 역할은 서로 다른 권한과 책임을 가집니다.
    """
    JUNIOR_ANALYST = "junior_analyst"      # 주니어 애널리스트: 조회만 가능
    SENIOR_MANAGER = "senior_manager"      # 시니어 매니저: 모든 권한

@dataclass
class UserSession:
    """
    [Session Management] 사용자 세션 정보
    
    현재 로그인한 사용자의 정보와 권한을 관리합니다.
    금융 시스템에서는 세션 추적이 감사(Audit) 목적으로 중요합니다.
    """
    user_id: str
    role: UserRole
    login_time: datetime
    permissions: Dict[str, bool]

class AuthenticationManager:
    """
    [Authentication Manager] 인증 및 권한 관리자
    
    사용자 로그인, 권한 확인, 세션 관리를 담당합니다.
    실제 금융 기관에서는 LDAP, Active Directory 등과 연동되지만,
    교육 목적으로 간단한 ID 기반 인증을 구현합니다.
    """
    
    def __init__(self):
        self.current_session: Optional[UserSession] = None
        self.logger = logging.getLogger(__name__)
        
        # [Permission Matrix] 역할별 권한 매트릭스
        # 실제 운영에서는 데이터베이스나 설정 파일에서 관리됩니다.
        self.role_permissions = {
            UserRole.JUNIOR_ANALYST: {
                "search_internal": True,      # 사내 데이터 검색 가능
                "search_web": True,           # 웹 검색 가능
                "get_stock_price": True,      # 주가 조회 가능
                "save_report": False,         # 리포트 저장 불가 (읽기 전용)
                "access_sensitive_data": False  # 민감 데이터 접근 불가
            },
            UserRole.SENIOR_MANAGER: {
                "search_internal": True,      # 사내 데이터 검색 가능
                "search_web": True,           # 웹 검색 가능
                "get_stock_price": True,      # 주가 조회 가능
                "save_report": True,          # 리포트 저장 가능
                "access_sensitive_data": True   # 민감 데이터 접근 가능
            }
        }
    
    def login(self, user_id: str) -> UserSession:
        """
        [User Login] 사용자 로그인 처리
        
        사용자 ID를 기반으로 역할을 결정하고 세션을 생성합니다.
        실제 시스템에서는 패스워드, 2FA 등 추가 인증이 필요하지만,
        교육 목적으로 ID 기반 간단 인증을 구현합니다.
        
        Args:
            user_id (str): 사용자 ID
            
        Returns:
            UserSession: 생성된 사용자 세션
        """
        # [Role Assignment] ID 패턴 기반 역할 할당
        # 실제 운영에서는 사용자 데이터베이스에서 조회합니다.
        if "senior" in user_id.lower():
            role = UserRole.SENIOR_MANAGER
            self.logger.info(f"[Authentication] {user_id} - SENIOR_MANAGER 권한 부여")
        else:
            role = UserRole.JUNIOR_ANALYST
            self.logger.info(f"[Authentication] {user_id} - JUNIOR_ANALYST 권한 부여")
        
        # [Session Creation] 사용자 세션 생성
        self.current_session = UserSession(
            user_id=user_id,
            role=role,
            login_time=datetime.now(),
            permissions=self.role_permissions[role].copy()
        )
        
        self.logger.info(f"[Authentication] 사용자 {user_id} 로그인 성공")
        return self.current_session
    
    def logout(self):
        """
        [User Logout] 사용자 로그아웃 처리
        
        현재 세션을 종료하고 보안을 위해 세션 정보를 정리합니다.
        """
        if self.current_session:
            user_id = self.current_session.user_id
            self.current_session = None
            self.logger.info(f"[Authentication] 사용자 {user_id} 로그아웃")
        else:
            self.logger.warning("[Authentication] 로그아웃 시도 - 활성 세션 없음")
    
    def get_current_user(self) -> Optional[UserSession]:
        """
        [Session Info] 현재 사용자 세션 정보 반환
        
        Returns:
            Optional[UserSession]: 현재 활성 세션 (없으면 None)
        """
        return self.current_session
    
    def is_logged_in(self) -> bool:
        """
        [Login Status] 로그인 상태 확인
        
        Returns:
            bool: 로그인 여부
        """
        return self.current_session is not None
    
    def check_permission(self, permission: str) -> bool:
        """
        [Permission Check] 권한 확인
        
        현재 사용자가 특정 작업을 수행할 권한이 있는지 확인합니다.
        이는 에이전트 도구에서 호출되어 보안을 강화합니다.
        
        Args:
            permission (str): 확인할 권한명
            
        Returns:
            bool: 권한 보유 여부
            
        Raises:
            PermissionError: 로그인하지 않았거나 권한이 없는 경우
        """
        # [Login Check] 로그인 상태 확인
        if not self.is_logged_in():
            self.logger.warning(f"[Permission Check] 미로그인 상태에서 {permission} 권한 요청")
            raise PermissionError("로그인이 필요합니다.")
        
        # [Permission Validation] 권한 확인
        has_permission = self.current_session.permissions.get(permission, False)
        
        if has_permission:
            self.logger.info(f"[Permission Check] {self.current_session.user_id} - {permission} 권한 승인")
        else:
            self.logger.warning(f"[Permission Check] {self.current_session.user_id} - {permission} 권한 거부")
            raise PermissionError(f"'{permission}' 권한이 없습니다. 관리자에게 문의하세요.")
        
        return has_permission
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        [User Info] 현재 사용자 정보 반환
        
        UI에서 사용자 정보를 표시하기 위한 메서드입니다.
        
        Returns:
            Dict[str, Any]: 사용자 정보 딕셔너리
        """
        if not self.is_logged_in():
            return {
                "logged_in": False,
                "user_id": None,
                "role": None,
                "permissions": {}
            }
        
        session = self.current_session
        return {
            "logged_in": True,
            "user_id": session.user_id,
            "role": session.role.value,
            "role_display": self._get_role_display_name(session.role),
            "login_time": session.login_time.strftime("%Y-%m-%d %H:%M:%S"),
            "permissions": session.permissions
        }
    
    def _get_role_display_name(self, role: UserRole) -> str:
        """
        [Role Display] 역할의 한국어 표시명 반환
        
        Args:
            role (UserRole): 사용자 역할
            
        Returns:
            str: 한국어 역할명
        """
        role_names = {
            UserRole.JUNIOR_ANALYST: "주니어 애널리스트",
            UserRole.SENIOR_MANAGER: "시니어 매니저"
        }
        return role_names.get(role, "알 수 없음")
    
    def get_permission_summary(self) -> str:
        """
        [Permission Summary] 현재 사용자의 권한 요약
        
        사용자가 자신의 권한을 쉽게 이해할 수 있도록 
        한국어로 권한을 요약해서 제공합니다.
        
        Returns:
            str: 권한 요약 텍스트
        """
        if not self.is_logged_in():
            return "로그인이 필요합니다."
        
        session = self.current_session
        role_display = self._get_role_display_name(session.role)
        
        # [Permission Description] 권한별 설명
        permission_descriptions = {
            "search_internal": "사내 데이터 검색",
            "search_web": "웹 검색",
            "get_stock_price": "주가 조회",
            "save_report": "리포트 저장",
            "access_sensitive_data": "민감 데이터 접근"
        }
        
        allowed_permissions = []
        denied_permissions = []
        
        for perm, allowed in session.permissions.items():
            desc = permission_descriptions.get(perm, perm)
            if allowed:
                allowed_permissions.append(desc)
            else:
                denied_permissions.append(desc)
        
        summary = f"**역할**: {role_display}\n\n"
        
        if allowed_permissions:
            summary += "**허용된 기능**:\n"
            for perm in allowed_permissions:
                summary += f"✅ {perm}\n"
        
        if denied_permissions:
            summary += "\n**제한된 기능**:\n"
            for perm in denied_permissions:
                summary += f"❌ {perm}\n"
        
        return summary


# [Global Instance] 전역 인증 관리자 인스턴스
# 앱 전체에서 하나의 인증 상태를 공유합니다.
auth_manager = AuthenticationManager()