"""
[Agent Tools] AI 에이전트 도구 함수 모음

이 모듈은 AI 에이전트가 실제 업무를 수행하기 위해 사용하는 도구들을 정의합니다.
모든 도구는 Governance Layer와 연동되어 권한 체크와 감사 로그를 자동으로 수행합니다.

교육 목표:
- smolagents의 @tool 데코레이터 활용법 학습
- Middleware 패턴을 통한 횡단 관심사(Cross-cutting Concerns) 처리
- 금융 데이터 API 연동 및 에러 처리 방법 이해
- 권한 기반 접근 제어(RBAC)의 실제 구현 방법 학습
"""

import os
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from functools import wraps

# [smolagents] AI 에이전트 도구 데코레이터
from smolagents import tool

# [Governance Layer] 권한 체크, 감사 로그, 보안 가드레일
from core.auth import auth_manager
from core.logger import audit_logger
from core.rag_engine import rag_engine

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)

def middleware_wrapper(func):
    """
    [Middleware Pattern] 도구 함수 미들웨어
    
    모든 도구 함수에 공통으로 적용되는 횡단 관심사를 처리합니다:
    - 감사 로그 기록 (모든 도구 호출 추적)
    - 에러 처리 및 로깅
    - 실행 시간 측정
    
    이는 금융 시스템에서 필수적인 투명성과 추적성을 보장합니다.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # [Audit Trail] 도구 호출 시작 로그
        user_session = auth_manager.get_current_user()
        user_id = user_session.user_id if user_session else "anonymous"
        
        start_time = datetime.now()
        
        # [Pre-execution Logging] 실행 전 감사 로그
        audit_logger.log_audit(
            user_id=user_id,
            action=f"TOOL_CALL_{func.__name__.upper()}",
            details={
                "tool_name": func.__name__,
                "arguments": {k: str(v)[:100] for k, v in kwargs.items()},  # 긴 인수는 잘라서 기록
                "start_time": start_time.isoformat()
            }
        )
        
        try:
            # [Tool Execution] 실제 도구 함수 실행
            result = func(*args, **kwargs)
            
            # [Success Logging] 성공 로그
            execution_time = (datetime.now() - start_time).total_seconds()
            audit_logger.log_audit(
                user_id=user_id,
                action=f"TOOL_SUCCESS_{func.__name__.upper()}",
                details={
                    "tool_name": func.__name__,
                    "execution_time_seconds": execution_time,
                    "result_type": type(result).__name__,
                    "result_length": len(str(result)) if result else 0
                }
            )
            
            return result
            
        except Exception as e:
            # [Error Logging] 에러 로그
            execution_time = (datetime.now() - start_time).total_seconds()
            audit_logger.log_security_event(
                user_id=user_id,
                event_type="TOOL_ERROR",
                message=f"도구 실행 실패: {func.__name__}",
                severity="WARNING",
                details={
                    "tool_name": func.__name__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "execution_time_seconds": execution_time
                }
            )
            
            # [User-friendly Error] 사용자에게 친화적인 에러 메시지 반환
            return f"도구 실행 중 오류가 발생했습니다: {str(e)}"
    
    return wrapper

@tool
@middleware_wrapper
def search_internal(query: str) -> str:
    """
    [Internal Knowledge Search] 사내 지식베이스 검색
    
    AI 에이전트가 "인터넷보다 먼저" 참고해야 할 사내 데이터를 검색합니다.
    금융 기관에서는 검증된 내부 정보를 우선적으로 활용하는 것이 원칙입니다.
    
    Args:
        query (str): 검색할 질의어
        
    Returns:
        str: 검색 결과 텍스트
    """
    try:
        # [Permission Check] 권한 확인 (모든 사용자에게 허용되지만 로그 기록)
        auth_manager.check_permission("search_internal")
        
        # [RAG Search] 벡터 검색 수행
        logger.info(f"[Internal Search] 사내 지식베이스 검색: {query}")
        
        # RAG 엔진을 통한 검색
        search_results = rag_engine.search(query, k=3)
        
        if not search_results:
            return "[사내 지식베이스] 관련 정보를 찾을 수 없습니다. 웹 검색을 시도해보세요."
        
        # [Result Formatting] 검색 결과 포맷팅
        formatted_results = []
        for i, result in enumerate(search_results, 1):
            formatted_result = (
                f"**[{i}] 출처: {result['source']} ({result['category']})**\n"
                f"{result['content']}\n"
            )
            formatted_results.append(formatted_result)
        
        final_result = "\n".join(formatted_results)
        
        # [Compliance Notice] 규제 준수 안내
        disclaimer = (
            "\n\n📋 **사내 데이터 기반 정보**\n"
            "위 정보는 사내 지식베이스에서 검색된 결과입니다. "
            "최신 정보 확인을 위해 추가 검색을 권장합니다."
        )
        
        return final_result + disclaimer
        
    except PermissionError as e:
        return f"권한 오류: {str(e)}"
    except Exception as e:
        logger.error(f"[Internal Search] 검색 실패: {e}")
        return f"사내 검색 중 오류가 발생했습니다: {str(e)}"

@tool
@middleware_wrapper
def search_web(query: str) -> str:
    """
    [Web Search] 웹 검색
    
    사내 데이터로 충분하지 않은 경우 외부 웹 검색을 수행합니다.
    실제 운영에서는 Serper, SerpAPI 등의 검색 API를 사용하지만,
    교육 목적으로 간단한 더미 검색 결과를 반환합니다.
    
    Args:
        query (str): 검색할 질의어
        
    Returns:
        str: 웹 검색 결과
    """
    try:
        # [Permission Check] 권한 확인
        auth_manager.check_permission("search_web")
        
        logger.info(f"[Web Search] 웹 검색 수행: {query}")
        
        # [API Integration] 실제 구현에서는 검색 API 호출
        # 교육 목적으로 더미 데이터 반환
        serper_api_key = os.getenv("SERPER_API_KEY")
        
        if serper_api_key and serper_api_key != "your_serper_api_key_here":
            # [Real API Call] 실제 API 호출 (키가 설정된 경우)
            try:
                headers = {
                    'X-API-KEY': serper_api_key,
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'q': query,
                    'num': 3,
                    'hl': 'ko',
                    'gl': 'kr'
                }
                
                response = requests.post(
                    'https://google.serper.dev/search',
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    for i, item in enumerate(data.get('organic', [])[:3], 1):
                        result = (
                            f"**[{i}] {item.get('title', 'N/A')}**\n"
                            f"출처: {item.get('link', 'N/A')}\n"
                            f"{item.get('snippet', 'N/A')}\n"
                        )
                        results.append(result)
                    
                    if results:
                        return "\n".join(results) + "\n\n🌐 **웹 검색 결과**\n위 정보는 외부 검색 결과이므로 신뢰성을 별도 확인하시기 바랍니다."
                
            except Exception as api_error:
                logger.warning(f"[Web Search] API 호출 실패: {api_error}")
        
        # [Fallback] 더미 검색 결과 (API 실패 시 또는 키 미설정 시)
        dummy_results = [
            {
                "title": f"'{query}' 관련 최신 뉴스",
                "snippet": f"{query}에 대한 최신 정보입니다. 자세한 내용은 관련 웹사이트를 참조하세요.",
                "url": "https://example.com/news"
            },
            {
                "title": f"'{query}' 분석 리포트",
                "snippet": f"{query}에 대한 전문가 분석 의견입니다. 투자 결정 시 신중한 검토가 필요합니다.",
                "url": "https://example.com/analysis"
            }
        ]
        
        formatted_results = []
        for i, result in enumerate(dummy_results, 1):
            formatted_result = (
                f"**[{i}] {result['title']}**\n"
                f"출처: {result['url']}\n"
                f"{result['snippet']}\n"
            )
            formatted_results.append(formatted_result)
        
        final_result = "\n".join(formatted_results)
        
        # [Demo Notice] 데모 안내
        disclaimer = (
            "\n\n🔍 **데모 검색 결과**\n"
            "실제 운영에서는 실시간 웹 검색 결과가 제공됩니다. "
            "현재는 교육용 더미 데이터입니다."
        )
        
        return final_result + disclaimer
        
    except PermissionError as e:
        return f"권한 오류: {str(e)}"
    except Exception as e:
        logger.error(f"[Web Search] 검색 실패: {e}")
        return f"웹 검색 중 오류가 발생했습니다: {str(e)}"

@tool
@middleware_wrapper
def get_stock_price(symbol: str) -> str:
    """
    [Stock Price] 주가 정보 조회
    
    Yahoo Finance API를 통해 실시간 주가 정보를 조회합니다.
    금융 AI 에이전트의 핵심 기능 중 하나입니다.
    
    Args:
        symbol (str): 주식 심볼 (예: "005930.KS" for 삼성전자)
        
    Returns:
        str: 주가 정보 텍스트
    """
    try:
        # [Permission Check] 권한 확인
        auth_manager.check_permission("get_stock_price")
        
        logger.info(f"[Stock Price] 주가 조회: {symbol}")
        
        # [Data Validation] 입력 검증
        if not symbol or len(symbol.strip()) == 0:
            return "주식 심볼을 입력해주세요."
        
        symbol = symbol.strip().upper()
        
        # [Yahoo Finance API] 주가 데이터 조회
        try:
            stock = yf.Ticker(symbol)
            
            # [Current Price] 현재가 정보
            info = stock.info
            hist = stock.history(period="5d")  # 최근 5일 데이터
            
            if hist.empty:
                return f"'{symbol}' 심볼의 주가 정보를 찾을 수 없습니다. 심볼을 확인해주세요."
            
            # [Price Analysis] 주가 분석
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price * 100) if prev_price != 0 else 0
            
            # [Volume Analysis] 거래량 분석
            current_volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].mean()
            
            # [Price Range] 가격 범위
            high_52w = hist['High'].max()
            low_52w = hist['Low'].min()
            
            # [Result Formatting] 결과 포맷팅
            change_indicator = "📈" if price_change >= 0 else "📉"
            
            result = f"""
**{symbol} 주가 정보** {change_indicator}

💰 **현재가**: {current_price:,.2f}원
📊 **전일 대비**: {price_change:+,.2f}원 ({price_change_pct:+.2f}%)
📈 **52주 최고**: {high_52w:,.2f}원
📉 **52주 최저**: {low_52w:,.2f}원
📦 **거래량**: {current_volume:,.0f}주 (평균 대비 {(current_volume/avg_volume*100):,.1f}%)

📅 **조회 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # [Company Info] 기업 정보 (가능한 경우)
            company_name = info.get('longName', info.get('shortName', 'N/A'))
            if company_name != 'N/A':
                result += f"\n🏢 **기업명**: {company_name}"
            
            # [Market Cap] 시가총액 (가능한 경우)
            market_cap = info.get('marketCap')
            if market_cap:
                market_cap_kr = market_cap / 1e12  # 조 단위로 변환
                result += f"\n💎 **시가총액**: {market_cap_kr:.2f}조원"
            
            # [Risk Disclaimer] 투자 위험 고지
            disclaimer = (
                "\n\n⚠️ **투자 유의사항**\n"
                "주가는 실시간으로 변동되며, 투자에는 원금 손실 위험이 있습니다. "
                "투자 결정 전 충분한 분석과 전문가 상담을 권장합니다."
            )
            
            return result + disclaimer
            
        except Exception as yf_error:
            logger.error(f"[Stock Price] Yahoo Finance API 오류: {yf_error}")
            return f"주가 조회 중 오류가 발생했습니다: {str(yf_error)}"
        
    except PermissionError as e:
        return f"권한 오류: {str(e)}"
    except Exception as e:
        logger.error(f"[Stock Price] 주가 조회 실패: {e}")
        return f"주가 조회 중 오류가 발생했습니다: {str(e)}"

@tool
@middleware_wrapper
def save_report(title: str, content: str) -> str:
    """
    [Save Report] 리포트 저장
    
    AI 에이전트가 생성한 리포트를 파일로 저장합니다.
    이 기능은 SENIOR_MANAGER 권한이 필요하며, 권한 체크의 실제 구현 예시입니다.
    
    Args:
        title (str): 리포트 제목
        content (str): 리포트 내용
        
    Returns:
        str: 저장 결과 메시지
    """
    try:
        # [Permission Check] 권한 확인 - 이 부분이 교육적으로 중요!
        # JUNIOR_ANALYST는 이 함수 호출 시 PermissionError 발생
        auth_manager.check_permission("save_report")
        
        logger.info(f"[Save Report] 리포트 저장 시도: {title}")
        
        # [Input Validation] 입력 검증
        if not title or not title.strip():
            return "리포트 제목을 입력해주세요."
        
        if not content or not content.strip():
            return "리포트 내용을 입력해주세요."
        
        # [File Path] 저장 경로 생성
        from pathlib import Path
        reports_dir = Path("./data/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # [File Name] 안전한 파일명 생성
        import re
        safe_title = re.sub(r'[^\w\s-]', '', title.strip())
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_title}.md"
        
        file_path = reports_dir / filename
        
        # [Report Content] 리포트 내용 구성
        user_session = auth_manager.get_current_user()
        report_header = f"""# {title}

**생성자**: {user_session.user_id if user_session else 'Unknown'}
**생성일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}
**시스템**: Quant-X Financial Research Portal

---

"""
        
        full_content = report_header + content
        
        # [File Save] 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # [Success Message] 성공 메시지
        success_message = f"""
✅ **리포트 저장 완료**

📄 **파일명**: {filename}
📁 **저장 경로**: {file_path}
📊 **파일 크기**: {len(full_content):,}자
⏰ **저장 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

리포트가 성공적으로 저장되었습니다.
"""
        
        return success_message
        
    except PermissionError as e:
        # [Permission Denied] 권한 거부 - 교육적으로 중요한 부분!
        error_message = f"""
❌ **권한 부족**

{str(e)}

💡 **해결 방법**: 
- SENIOR_MANAGER 권한이 필요합니다
- 관리자에게 권한 승급을 요청하세요
- 현재는 조회 기능만 이용 가능합니다
"""
        return error_message
        
    except Exception as e:
        logger.error(f"[Save Report] 리포트 저장 실패: {e}")
        return f"리포트 저장 중 오류가 발생했습니다: {str(e)}"

@tool
@middleware_wrapper
def get_market_summary() -> str:
    """
    [Market Summary] 시장 요약 정보
    
    주요 지수와 시장 현황을 요약해서 제공합니다.
    실제 운영에서는 실시간 데이터를 사용하지만, 교육 목적으로 더미 데이터를 포함합니다.
    
    Returns:
        str: 시장 요약 정보
    """
    try:
        # [Permission Check] 권한 확인
        auth_manager.check_permission("get_stock_price")  # 주가 조회 권한 재사용
        
        logger.info("[Market Summary] 시장 요약 정보 조회")
        
        # [Major Indices] 주요 지수 조회
        indices = {
            "^KS11": "코스피",      # KOSPI
            "^KQ11": "코스닥",      # KOSDAQ
            "^DJI": "다우존스",     # Dow Jones
            "^IXIC": "나스닥"       # NASDAQ
        }
        
        market_data = []
        
        for symbol, name in indices.items():
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="2d")
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    change = current - prev
                    change_pct = (change / prev * 100) if prev != 0 else 0
                    
                    indicator = "📈" if change >= 0 else "📉"
                    
                    market_data.append({
                        "name": name,
                        "current": current,
                        "change": change,
                        "change_pct": change_pct,
                        "indicator": indicator
                    })
                    
            except Exception as e:
                logger.warning(f"[Market Summary] {name} 데이터 조회 실패: {e}")
                # 더미 데이터로 대체
                market_data.append({
                    "name": name,
                    "current": 2500.0,
                    "change": 10.5,
                    "change_pct": 0.42,
                    "indicator": "📈"
                })
        
        # [Summary Formatting] 요약 정보 포맷팅
        summary = "📊 **주요 지수 현황**\n\n"
        
        for data in market_data:
            summary += (
                f"{data['indicator']} **{data['name']}**: "
                f"{data['current']:,.2f} "
                f"({data['change']:+,.2f}, {data['change_pct']:+.2f}%)\n"
            )
        
        # [Market News] 시장 뉴스 (더미)
        summary += "\n📰 **주요 시장 뉴스**\n"
        summary += "• 한국은행 기준금리 동결 결정\n"
        summary += "• 반도체 업종 상승세 지속\n"
        summary += "• 외국인 투자자 순매수 전환\n"
        
        # [Timestamp] 조회 시간
        summary += f"\n⏰ **조회 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # [Disclaimer] 면책 조항
        disclaimer = (
            "\n\n⚠️ **투자 유의사항**\n"
            "시장 정보는 참고용이며, 실시간 변동 가능합니다. "
            "투자 결정 시 최신 정보를 별도 확인하시기 바랍니다."
        )
        
        return summary + disclaimer
        
    except PermissionError as e:
        return f"권한 오류: {str(e)}"
    except Exception as e:
        logger.error(f"[Market Summary] 시장 요약 조회 실패: {e}")
        return f"시장 요약 조회 중 오류가 발생했습니다: {str(e)}"

# [Tool Registry] 도구 목록 (디버깅 및 관리용)
AVAILABLE_TOOLS = [
    {
        "name": "search_internal",
        "description": "사내 지식베이스 검색",
        "required_permission": "search_internal",
        "category": "knowledge"
    },
    {
        "name": "search_web", 
        "description": "웹 검색",
        "required_permission": "search_web",
        "category": "knowledge"
    },
    {
        "name": "get_stock_price",
        "description": "주가 정보 조회",
        "required_permission": "get_stock_price", 
        "category": "financial_data"
    },
    {
        "name": "save_report",
        "description": "리포트 저장",
        "required_permission": "save_report",
        "category": "output"
    },
    {
        "name": "get_market_summary",
        "description": "시장 요약 정보",
        "required_permission": "get_stock_price",
        "category": "financial_data"
    }
]

def get_available_tools_for_user() -> List[Dict[str, Any]]:
    """
    [Tool Access] 현재 사용자가 사용 가능한 도구 목록 반환
    
    사용자의 권한에 따라 접근 가능한 도구만 필터링하여 반환합니다.
    
    Returns:
        List[Dict[str, Any]]: 사용 가능한 도구 목록
    """
    if not auth_manager.is_logged_in():
        return []
    
    user_session = auth_manager.get_current_user()
    available_tools = []
    
    for tool_info in AVAILABLE_TOOLS:
        permission = tool_info["required_permission"]
        if user_session.permissions.get(permission, False):
            available_tools.append(tool_info)
    
    return available_tools