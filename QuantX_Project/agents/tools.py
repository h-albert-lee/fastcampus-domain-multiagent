"""
[AI Agent Tools] 금융 리서치를 위한 도구 함수들
- 모든 도구는 거버넌스 레이어의 통제를 받음 (미들웨어 패턴)
- 사용자 권한 체크 및 감사 로그 자동 기록
- DuckDuckGo 검색으로 API 키 없는 웹 검색 지원
- 실패에 강한 설계로 안정적인 서비스 제공
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import wraps

# [External APIs] 외부 서비스 연동
import yfinance as yf
from duckduckgo_search import DDGS  # [무료 검색] API 키 불필요한 웹 검색 서비스

# [smolagents Integration] AI 에이전트 도구 데코레이터
try:
    from smolagents import tool
    SMOLAGENTS_AVAILABLE = True
except ImportError:
    # smolagents가 없는 경우 더미 데코레이터 제공
    def tool(func):
        return func
    SMOLAGENTS_AVAILABLE = False

# [Internal Modules] 거버넌스 레이어 모듈들
from core.auth import auth_manager
from core.logger import get_logger
from core.rag_engine import rag_engine

logger = get_logger(__name__)


def middleware_wrapper(func):
    """
    [미들웨어 패턴] 모든 도구 함수에 적용되는 공통 처리 로직
    
    핵심 기능:
    1. 감사 로그 자동 기록 - 금융사고 방지 및 규제 준수를 위해 모든 도구 호출 내역을 변조 불가능한 로그로 기록
    2. 에러 처리 - 도구 실행 실패 시 시스템이 죽지 않고 적절한 오류 메시지 반환
    3. 성능 모니터링 - 각 도구의 실행 시간 측정 및 기록
    
    이 패턴을 통해 AI 에이전트는 자신이 감시받고 있다는 것을 모르면서도
    모든 행위가 투명하게 기록되어 금융권의 엄격한 감사 요구사항을 충족합니다.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        tool_name = func.__name__
        
        try:
            # [감사 로그] 도구 호출 시작 기록
            logger.info(f"[Tool Execution] {tool_name} 실행 시작 - Args: {args}, Kwargs: {kwargs}")
            
            # [실제 도구 실행] 원본 함수 호출
            result = func(*args, **kwargs)
            
            # [성능 측정] 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # [감사 로그] 성공적인 실행 기록
            logger.info(f"[Tool Execution] {tool_name} 실행 완료 - 소요시간: {execution_time:.2f}초")
            
            return result
            
        except Exception as e:
            # [에러 처리] 도구 실행 실패 시 로그 기록 및 사용자 친화적 메시지 반환
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"[Tool Execution] {tool_name} 실행 실패 - 오류: {str(e)}, 소요시간: {execution_time:.2f}초")
            
            return f"❌ {tool_name} 실행 중 오류가 발생했습니다: {str(e)}"
    
    return wrapper


@tool
@middleware_wrapper
def search_internal(query: str) -> str:
    """
    [사내 지식베이스 검색] 
    HuggingFace 데이터셋 기반 RAG 시스템을 통해 사내 금융 데이터를 검색
    
    이 도구는 금융 기관의 핵심 원칙인 "사내 데이터 우선 정책"을 구현합니다.
    외부 정보보다 검증된 내부 데이터를 먼저 활용하여 정확성과 신뢰성을 확보합니다.
    
    Args:
        query (str): 검색할 질의어
        
    Returns:
        str: 검색 결과 (출처 정보 포함)
    """
    try:
        logger.info(f"[Internal Search] 사내 지식베이스 검색 시작 - 질의: {query}")
        
        # [RAG 검색] 벡터 유사도 기반 문서 검색
        results = rag_engine.search(query, k=3)
        
        if not results:
            return "🔍 **사내 검색 결과**\n\n관련된 사내 문서를 찾을 수 없습니다. 외부 검색을 시도해보세요."
        
        # [결과 포맷팅] 출처 정보와 함께 검색 결과 구성
        formatted_results = "🔍 **사내 지식베이스 검색 결과**\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"**{i}. [출처: 사내 데이터]**\n{result}\n\n"
        
        logger.info(f"[Internal Search] 검색 완료 - {len(results)}개 결과 반환")
        return formatted_results
        
    except Exception as e:
        logger.error(f"[Internal Search] 검색 실패: {str(e)}")
        return f"❌ **사내 검색 오류**\n\n지식베이스 검색 중 오류가 발생했습니다: {str(e)}"


@tool
@middleware_wrapper  
def search_web(query: str) -> str:
    """
    [웹 검색] DuckDuckGo를 통한 무료 웹 검색
    
    기존 Serper API(유료) 대신 DuckDuckGo Search를 사용하여 학생들의 실습 진입장벽을 제거했습니다.
    API 키가 필요 없어 즉시 사용 가능하며, 개인정보 보호에도 우수한 검색 엔진입니다.
    
    주의사항:
    - 사내 데이터 검색 후 보완적으로만 사용해야 합니다
    - 검색 결과는 참고용이며, 투자 결정의 근거로 사용해서는 안 됩니다
    
    Args:
        query (str): 검색할 질의어
        
    Returns:
        str: 웹 검색 결과 (제목, 출처, 요약 포함)
    """
    try:
        logger.info(f"[Web Search] DuckDuckGo 웹 검색 시작 - 질의: {query}")
        
        # [DuckDuckGo 검색] 무료 검색 API 사용 (API 키 불필요)
        # max_results=3으로 제한하여 응답 속도 최적화 및 과도한 정보 방지
        with DDGS() as ddgs:
            search_results = list(ddgs.text(
                keywords=query,
                max_results=3,  # [성능 최적화] 상위 3개 결과만 가져와 응답 속도 향상
                region='kr-ko',  # [지역화] 한국 관련 결과 우선 표시
                safesearch='moderate'  # [안전 검색] 부적절한 콘텐츠 필터링
            ))
        
        if not search_results:
            return "🌐 **웹 검색 결과**\n\n관련된 웹 페이지를 찾을 수 없습니다. 다른 검색어를 시도해보세요."
        
        # [결과 포맷팅] 사용자 친화적인 형태로 검색 결과 구성
        formatted_results = "🌐 **웹 검색 결과**\n\n"
        for i, result in enumerate(search_results, 1):
            title = result.get('title', '제목 없음')
            url = result.get('href', '')
            body = result.get('body', '내용 없음')
            
            # [내용 요약] 너무 긴 내용은 200자로 제한
            if len(body) > 200:
                body = body[:200] + "..."
            
            formatted_results += f"**{i}. {title}**\n"
            formatted_results += f"📍 출처: {url}\n"
            formatted_results += f"📄 요약: {body}\n\n"
        
        # [규제 준수 경고] 웹 검색 결과 사용 시 주의사항 안내
        formatted_results += "⚠️ **주의사항**: 웹 검색 결과는 참고용이며, 투자 결정에 사용하지 마세요.\n"
        
        logger.info(f"[Web Search] 검색 완료 - {len(search_results)}개 결과 반환")
        return formatted_results
        
    except Exception as e:
        # [에러 처리] DuckDuckGo 서비스 장애 시 사용자 친화적 메시지 제공
        logger.error(f"[Web Search] DuckDuckGo 검색 실패: {str(e)}")
        return "❌ **웹 검색 서비스 일시적 오류**\n\n검색 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요."


@tool
@middleware_wrapper
def get_stock_price(symbol: str) -> str:
    """
    [주가 정보 조회] Yahoo Finance API를 통한 실시간 주가 데이터 조회
    
    한국 주식의 경우 심볼 뒤에 '.KS' (코스피) 또는 '.KQ' (코스닥)를 붙여야 합니다.
    예: 삼성전자 = '005930.KS', 카카오 = '035720.KS'
    
    Args:
        symbol (str): 주식 심볼 (예: '005930.KS', 'AAPL')
        
    Returns:
        str: 주가 정보 (현재가, 변동률, 거래량 등) + UI용 차트 데이터
    """
    try:
        logger.info(f"[Stock Price] 주가 조회 시작 - 심볼: {symbol}")
        
        # [Yahoo Finance API] 주식 정보 조회
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1d")
        
        if hist.empty:
            return f"❌ **주가 조회 실패**\n\n'{symbol}' 심볼을 찾을 수 없습니다. 올바른 심볼인지 확인해주세요."
        
        # [주가 데이터 추출] 최신 거래일 기준 정보
        current_price = hist['Close'].iloc[-1]
        prev_close = info.get('previousClose', current_price)
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
        volume = hist['Volume'].iloc[-1]
        
        # [차트용 데이터 수집] UI에서 활용할 수 있도록 더 많은 기간의 데이터 수집
        hist_30d = stock.history(period="30d")
        
        # [UI용 차트 데이터 저장] 세션 상태에 저장하여 UI에서 활용
        from agents.core import AGENT_SESSION_STATE
        chart_data = {
            "symbol": symbol,
            "dates": hist_30d.index.strftime('%Y-%m-%d').tolist(),
            "prices": hist_30d['Close'].tolist(),
            "volumes": hist_30d['Volume'].tolist(),
            "highs": hist_30d['High'].tolist(),
            "lows": hist_30d['Low'].tolist(),
            "current_price": float(current_price),
            "change": float(change),
            "change_percent": float(change_percent),
            "volume": int(volume),
            "timestamp": datetime.now().isoformat()
        }
        
        # [중간 산출물 저장] UI에서 차트를 그릴 수 있도록 데이터 저장
        AGENT_SESSION_STATE["intermediate_outputs"][f"stock_data_{symbol}"] = chart_data
        
        # [결과 포맷팅] 금융 전문가 수준의 상세 정보 제공
        company_name = info.get('longName', symbol)
        market_cap = info.get('marketCap', 'N/A')
        
        result = f"📈 **주가 정보: {company_name} ({symbol})**\n\n"
        result += f"💰 **현재가**: {current_price:,.0f}원\n"
        result += f"📊 **전일대비**: {change:+,.0f}원 ({change_percent:+.2f}%)\n"
        result += f"📦 **거래량**: {volume:,}주\n"
        
        if market_cap != 'N/A':
            result += f"🏢 **시가총액**: {market_cap:,}원\n"
        
        result += f"🕐 **조회시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # [차트 데이터 정보 추가] UI에서 차트를 확인할 수 있음을 안내
        result += f"📊 **차트 데이터**: 최근 30일 데이터가 시각화용으로 저장되었습니다.\n"
        result += f"   - 데이터 포인트: {len(hist_30d)}개\n"
        result += f"   - 최고가: {hist_30d['High'].max():,.0f}원\n"
        result += f"   - 최저가: {hist_30d['Low'].min():,.0f}원\n\n"
        
        result += "⚠️ **투자 유의사항**: 본 정보는 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다."
        
        logger.info(f"[Stock Price] 주가 조회 완료 - {symbol}: {current_price:,.0f}원, 차트 데이터 {len(hist_30d)}개 저장")
        return result
        
    except Exception as e:
        logger.error(f"[Stock Price] 주가 조회 실패 - {symbol}: {str(e)}")
        return f"❌ **주가 조회 오류**\n\n'{symbol}' 주가 조회 중 오류가 발생했습니다: {str(e)}"


@tool
@middleware_wrapper
def save_report(title: str, content: str) -> str:
    """
    [리포트 저장] 분석 결과를 파일로 저장
    
    이 기능은 Senior Manager 권한이 필요합니다.
    Junior Analyst는 조회만 가능하고 저장은 불가능하여 정보 보안을 유지합니다.
    
    Args:
        title (str): 리포트 제목
        content (str): 리포트 내용
        
    Returns:
        str: 저장 결과 메시지
    """
    try:
        # [권한 체크] Senior Manager만 리포트 저장 가능
        # 이는 금융 기관의 정보 보안 정책을 반영한 것입니다
        user_id = auth_manager.current_user_id
        if not auth_manager.check_permission(user_id, 'save_report'):
            logger.warning(f"[Save Report] 권한 없음 - 사용자: {user_id}")
            return "❌ **권한 부족**\n\n리포트 저장 권한이 없습니다. Senior Manager만 저장 가능합니다."
        
        logger.info(f"[Save Report] 리포트 저장 시작 - 제목: {title}")
        
        # [파일 저장] data/reports 디렉토리에 마크다운 형식으로 저장
        os.makedirs("data/reports", exist_ok=True)
        
        # [파일명 생성] 타임스탬프와 제목을 조합하여 고유한 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"data/reports/{timestamp}_{safe_title[:50]}.md"
        
        # [리포트 내용 구성] 메타데이터와 함께 저장
        report_content = f"""# {title}

**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**작성자**: {user_id}
**시스템**: Quant-X Financial Research Portal

---

{content}

---

*본 리포트는 Quant-X 시스템에서 자동 생성되었습니다.*
*투자 결정에 대한 책임은 투자자 본인에게 있습니다.*
"""
        
        # [파일 쓰기] UTF-8 인코딩으로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"[Save Report] 리포트 저장 완료 - 파일: {filename}")
        return f"✅ **리포트 저장 완료**\n\n파일명: {filename}\n저장 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
    except Exception as e:
        logger.error(f"[Save Report] 리포트 저장 실패: {str(e)}")
        return f"❌ **리포트 저장 오류**\n\n저장 중 오류가 발생했습니다: {str(e)}"


@tool
@middleware_wrapper
def get_market_summary() -> str:
    """
    [시장 현황 요약] 주요 지수 및 시장 동향 정보 제공
    
    코스피, 코스닥, 다우존스, 나스닥 등 주요 지수의 현재 상황을 요약하여 제공합니다.
    시장 전반의 흐름을 파악하는 데 유용합니다.
    
    Returns:
        str: 시장 현황 요약 정보 + UI용 차트 데이터
    """
    try:
        logger.info("[Market Summary] 시장 현황 요약 시작")
        
        # [주요 지수 목록] 한국 및 미국 주요 지수
        indices = {
            "코스피": "^KS11",
            "코스닥": "^KQ11", 
            "다우존스": "^DJI",
            "나스닥": "^IXIC",
            "S&P 500": "^GSPC"
        }
        
        summary = "📊 **주요 지수 현황**\n\n"
        market_data = {}  # UI용 시장 데이터 저장
        
        for name, symbol in indices.items():
            try:
                # [지수 데이터 조회] 각 지수별 최신 정보 수집
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")  # 2일치 데이터로 전일 대비 계산
                hist_7d = ticker.history(period="7d")  # 7일치 데이터로 차트용 데이터 수집
                
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2]
                    change = current - previous
                    change_percent = (change / previous) * 100
                    
                    # [변동률에 따른 이모지] 시각적 효과 추가
                    emoji = "🔴" if change < 0 else "🟢" if change > 0 else "⚪"
                    
                    summary += f"{emoji} **{name}**: {current:,.2f} ({change:+.2f}, {change_percent:+.2f}%)\n"
                    
                    # [UI용 데이터 저장] 차트 생성을 위한 데이터 수집
                    if len(hist_7d) > 0:
                        market_data[name] = {
                            "symbol": symbol,
                            "current": float(current),
                            "change": float(change),
                            "change_percent": float(change_percent),
                            "dates": hist_7d.index.strftime('%Y-%m-%d').tolist(),
                            "values": hist_7d['Close'].tolist(),
                            "volumes": hist_7d['Volume'].tolist() if 'Volume' in hist_7d.columns else []
                        }
                else:
                    summary += f"⚪ **{name}**: 데이터 없음\n"
                    
            except Exception as e:
                logger.warning(f"[Market Summary] {name} 조회 실패: {str(e)}")
                summary += f"⚪ **{name}**: 조회 실패\n"
        
        # [UI용 시장 데이터 저장] 세션 상태에 저장하여 UI에서 활용
        from agents.core import AGENT_SESSION_STATE
        AGENT_SESSION_STATE["intermediate_outputs"]["market_summary"] = {
            "indices": market_data,
            "timestamp": datetime.now().isoformat(),
            "total_indices": len(market_data)
        }
        
        # [시장 분석 코멘트] 전반적인 시장 상황 요약
        summary += f"\n🕐 **업데이트**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # [차트 데이터 정보 추가] UI에서 차트를 확인할 수 있음을 안내
        summary += f"📊 **차트 데이터**: {len(market_data)}개 지수의 7일간 데이터가 시각화용으로 저장되었습니다.\n"
        
        # [시장 동향 분석] 상승/하락 지수 개수 계산
        up_count = sum(1 for data in market_data.values() if data.get('change', 0) > 0)
        down_count = sum(1 for data in market_data.values() if data.get('change', 0) < 0)
        
        summary += f"   - 상승 지수: {up_count}개\n"
        summary += f"   - 하락 지수: {down_count}개\n"
        summary += f"   - 데이터 포인트: 각 지수별 7일간 데이터\n\n"
        
        summary += "📈 **시장 분석**: 위 지수들의 움직임을 종합하여 전반적인 시장 흐름을 파악하세요.\n\n"
        summary += "⚠️ **투자 유의사항**: 지수 정보는 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다."
        
        logger.info(f"[Market Summary] 시장 현황 요약 완료 - {len(market_data)}개 지수 데이터 저장")
        return summary
        
    except Exception as e:
        logger.error(f"[Market Summary] 시장 현황 조회 실패: {str(e)}")
        return f"❌ **시장 현황 조회 오류**\n\n시장 데이터 조회 중 오류가 발생했습니다: {str(e)}"


def get_all_tools(user_id: str) -> List:
    """
    [도구 목록 반환] 사용자 권한에 따라 사용 가능한 도구 목록을 반환
    
    모든 도구는 미들웨어 패턴을 통해 감사 로그와 권한 체크가 자동으로 적용됩니다.
    이는 금융 기관의 엄격한 보안 요구사항을 충족하기 위한 설계입니다.
    
    Args:
        user_id (str): 사용자 ID
        
    Returns:
        List: 사용 가능한 도구 함수들의 리스트
    """
    logger.info(f"[Tools] 사용자 {user_id}를 위한 도구 목록 생성")
    
    # [기본 도구] 모든 사용자가 사용 가능한 도구들
    tools = [
        search_internal,    # 사내 지식베이스 검색 (최우선)
        search_web,         # DuckDuckGo 웹 검색 (무료, API 키 불필요)
        get_stock_price,    # Yahoo Finance 주가 조회
        get_market_summary  # 시장 현황 요약
    ]
    
    # [권한별 도구] Senior Manager만 사용 가능한 고급 기능
    if auth_manager.check_permission(user_id, 'save_report'):
        tools.append(save_report)  # 리포트 저장 기능
        logger.info(f"[Tools] Senior Manager 권한 확인 - save_report 도구 추가")
    
    logger.info(f"[Tools] 총 {len(tools)}개 도구 반환 완료")
    return tools