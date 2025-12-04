"""
[Knowledge Management] RAG 엔진 - 사내 금융 지식 검색 시스템

이 모듈은 금융 엔터프라이즈에서 AI 에이전트가 "인터넷보다 먼저" 참고해야 할 
사내 지식소를 관리합니다. 규제 준수와 정보 보안을 위해 검증된 내부 데이터를 
우선적으로 활용하는 것이 금융권 AI의 핵심 원칙입니다.

교육 목표:
- HuggingFace 데이터셋을 활용한 실제 금융 데이터 로딩
- LangChain을 통한 문서 청킹(Chunking) 전략 이해
- FAISS 벡터 인덱스 구축 및 캐싱 메커니즘 학습
- 싱글톤 패턴을 통한 리소스 효율적 관리
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# [Vector Search] 고속 유사도 검색을 위한 FAISS 라이브러리
import faiss

# [Data Processing] HuggingFace 데이터셋 및 pandas 데이터 처리
from datasets import load_dataset
import pandas as pd

# [LangChain RAG Components] 문서 처리 및 벡터 저장소 구성
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# [Environment] 환경변수 로드
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class RAGEngine:
    """
    [Singleton Pattern] 사내 금융 지식 검색 엔진
    
    금융 시스템에서는 메모리와 API 호출 비용을 최적화하기 위해 
    RAG 엔진을 싱글톤으로 구현합니다. 앱 실행 시 한 번만 초기화되어
    모든 에이전트가 동일한 지식베이스를 공유합니다.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """싱글톤 패턴 구현 - 인스턴스가 하나만 생성되도록 보장"""
        if cls._instance is None:
            cls._instance = super(RAGEngine, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        [Lazy Initialization] 지연 초기화 패턴
        
        실제 검색이 요청될 때까지 무거운 초기화 작업을 지연시켜
        앱 시작 시간을 단축합니다.
        """
        if not self._initialized:
            self.vector_store = None
            self.embeddings = None
            self.logger = logging.getLogger(__name__)
            self._setup_directories()
            RAGEngine._initialized = True
    
    def _setup_directories(self):
        """
        [File System Management] 벡터 저장소 디렉토리 설정
        
        금융 시스템에서는 데이터 저장 위치가 규제 대상이므로
        명확한 디렉토리 구조를 유지해야 합니다.
        """
        self.data_dir = Path("./data")
        self.vector_store_dir = self.data_dir / "vector_store"
        self.reports_dir = self.data_dir / "reports"
        
        # 디렉토리 생성 (존재하지 않는 경우)
        self.data_dir.mkdir(exist_ok=True)
        self.vector_store_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
    
    def _initialize_embeddings(self):
        """
        [Embeddings Model] OpenAI 임베딩 모델 초기화
        
        금융 도메인에서는 일관된 임베딩 품질이 중요하므로
        검증된 OpenAI 모델을 사용합니다.
        """
        try:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-ada-002",  # 금융 텍스트에 최적화된 모델
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            self.logger.info("[RAG Engine] OpenAI 임베딩 모델 초기화 완료")
        except Exception as e:
            self.logger.error(f"[RAG Engine] 임베딩 모델 초기화 실패: {e}")
            raise
    
    def _load_financial_datasets(self) -> List[Document]:
        """
        [Data Source] HuggingFace 금융 데이터셋 로드
        
        실제 금융 기관에서는 내부 데이터베이스를 연동하지만,
        교육 목적으로 공개된 한국어 금융 데이터셋을 활용합니다.
        
        Returns:
            List[Document]: LangChain Document 객체 리스트
        """
        documents = []
        
        try:
            # [Dataset 1] 공시 데이터 - 기업 공시 정보
            self.logger.info("[Data Loading] 공시 데이터 로딩 중...")
            dart_dataset = load_dataset(
                "nmixx-fin/synthetic_dart_report_korean", 
                split="train"
            )
            
            # 공시 데이터를 Document 객체로 변환
            for item in dart_dataset:
                doc = Document(
                    page_content=item["text"],
                    metadata={
                        "source": "공시",
                        "category": item.get("category", "공시"),
                        "doc_type": "dart_report"
                    }
                )
                documents.append(doc)
            
            self.logger.info(f"[Data Loading] 공시 데이터 {len(dart_dataset)}건 로드 완료")
            
        except Exception as e:
            self.logger.warning(f"[Data Loading] 공시 데이터 로드 실패: {e}")
        
        try:
            # [Dataset 2] 금융 리포트 - 시황 분석 및 투자 의견
            self.logger.info("[Data Loading] 금융 리포트 데이터 로딩 중...")
            report_dataset = load_dataset(
                "nmixx-fin/synthetic_financial_report_korean", 
                split="train"
            )
            
            # 리포트 데이터를 Document 객체로 변환
            for item in report_dataset:
                doc = Document(
                    page_content=item["text"],
                    metadata={
                        "source": "리포트",
                        "category": item.get("category", "시황"),
                        "doc_type": "financial_report"
                    }
                )
                documents.append(doc)
            
            self.logger.info(f"[Data Loading] 리포트 데이터 {len(report_dataset)}건 로드 완료")
            
        except Exception as e:
            self.logger.warning(f"[Data Loading] 리포트 데이터 로드 실패: {e}")
        
        if not documents:
            # 데이터 로드에 실패한 경우 더미 데이터 생성 (교육용)
            self.logger.warning("[Data Loading] 실제 데이터 로드 실패, 더미 데이터 생성")
            documents = self._create_dummy_documents()
        
        return documents
    
    def _create_dummy_documents(self) -> List[Document]:
        """
        [Fallback Data] 더미 금융 데이터 생성
        
        실제 데이터 로드에 실패한 경우를 대비한 교육용 더미 데이터입니다.
        실제 운영 환경에서는 이런 fallback 메커니즘이 중요합니다.
        """
        dummy_data = [
            {
                "text": "삼성전자는 2024년 3분기 실적에서 메모리 반도체 부문의 회복세를 보이며 전년 동기 대비 매출이 증가했습니다. 특히 AI 서버용 고대역폭 메모리(HBM) 수요 증가가 주요 성장 동력으로 작용했습니다.",
                "source": "공시",
                "category": "실적"
            },
            {
                "text": "한국은행이 기준금리를 3.50%로 동결하기로 결정했습니다. 인플레이션 압력과 경제성장률을 종합적으로 고려한 결과로, 당분간 통화정책 기조를 유지할 것으로 예상됩니다.",
                "source": "리포트",
                "category": "시황"
            },
            {
                "text": "코스피 지수는 최근 외국인 투자자들의 순매수세에 힘입어 2,600선을 회복했습니다. 특히 기술주와 바이오주를 중심으로 한 성장주에 대한 관심이 높아지고 있습니다.",
                "source": "리포트",
                "category": "시황"
            }
        ]
        
        documents = []
        for item in dummy_data:
            doc = Document(
                page_content=item["text"],
                metadata={
                    "source": item["source"],
                    "category": item["category"],
                    "doc_type": "dummy_data"
                }
            )
            documents.append(doc)
        
        return documents
    
    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        [Text Chunking] 문서 청킹 전략
        
        금융 문서는 길이가 다양하므로 적절한 크기로 분할하여
        검색 정확도를 높입니다. 청킹 크기는 임베딩 모델의 
        토큰 제한과 검색 품질을 고려하여 설정합니다.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,        # [Chunk Size] 1000자 단위로 분할
            chunk_overlap=200,      # [Overlap] 200자 중복으로 문맥 보존
            length_function=len,    # 한국어 문자 기준 길이 계산
            separators=["\n\n", "\n", ".", "!", "?", " ", ""]  # 자연스러운 분할점
        )
        
        chunked_docs = text_splitter.split_documents(documents)
        self.logger.info(f"[Text Chunking] {len(documents)}개 문서를 {len(chunked_docs)}개 청크로 분할")
        
        return chunked_docs
    
    def _build_vector_index(self, documents: List[Document]):
        """
        [Vector Index] FAISS 벡터 인덱스 구축
        
        문서들을 벡터로 변환하여 고속 유사도 검색이 가능한
        FAISS 인덱스를 구축합니다. 금융 데이터의 특성상
        정확한 검색이 중요하므로 품질 높은 임베딩을 사용합니다.
        """
        try:
            self.logger.info("[Vector Index] FAISS 벡터 인덱스 구축 중...")
            
            # LangChain FAISS 벡터 저장소 생성
            self.vector_store = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            # [Caching] 벡터 인덱스를 로컬에 저장하여 재시작 시 빠른 로딩
            self.vector_store.save_local(str(self.vector_store_dir))
            
            self.logger.info(f"[Vector Index] {len(documents)}개 문서의 벡터 인덱스 구축 완료")
            
        except Exception as e:
            self.logger.error(f"[Vector Index] 벡터 인덱스 구축 실패: {e}")
            raise
    
    def _load_cached_index(self) -> bool:
        """
        [Cache Loading] 캐시된 벡터 인덱스 로드
        
        이미 구축된 벡터 인덱스가 있다면 로드하여 초기화 시간을 단축합니다.
        금융 시스템에서는 빠른 응답 시간이 중요하므로 캐싱 전략이 필수입니다.
        
        Returns:
            bool: 캐시 로드 성공 여부
        """
        try:
            # 벡터 저장소 파일 존재 확인
            index_file = self.vector_store_dir / "index.faiss"
            if not index_file.exists():
                return False
            
            self.logger.info("[Cache Loading] 캐시된 벡터 인덱스 로드 중...")
            
            # 임베딩 모델 초기화 (캐시 로드에도 필요)
            self._initialize_embeddings()
            
            # FAISS 벡터 저장소 로드
            self.vector_store = FAISS.load_local(
                str(self.vector_store_dir),
                self.embeddings,
                allow_dangerous_deserialization=True  # 교육용으로만 사용
            )
            
            self.logger.info("[Cache Loading] 캐시된 벡터 인덱스 로드 완료")
            return True
            
        except Exception as e:
            self.logger.warning(f"[Cache Loading] 캐시 로드 실패: {e}")
            return False
    
    def initialize(self):
        """
        [Initialization] RAG 엔진 초기화
        
        캐시된 인덱스가 있으면 로드하고, 없으면 새로 구축합니다.
        이는 금융 시스템의 효율성과 안정성을 위한 핵심 로직입니다.
        """
        if self.vector_store is not None:
            return  # 이미 초기화됨
        
        # 1단계: 캐시된 인덱스 로드 시도
        if self._load_cached_index():
            return
        
        # 2단계: 새로운 인덱스 구축
        self.logger.info("[RAG Engine] 새로운 벡터 인덱스 구축 시작")
        
        # 임베딩 모델 초기화
        self._initialize_embeddings()
        
        # 금융 데이터셋 로드
        documents = self._load_financial_datasets()
        
        # 문서 청킹
        chunked_docs = self._chunk_documents(documents)
        
        # 벡터 인덱스 구축
        self._build_vector_index(chunked_docs)
        
        self.logger.info("[RAG Engine] RAG 엔진 초기화 완료")
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        [Knowledge Search] 사내 지식 검색
        
        에이전트가 질문에 답하기 위해 사내 지식베이스를 검색합니다.
        금융 도메인에서는 정확하고 신뢰할 수 있는 정보가 중요하므로
        출처와 함께 결과를 반환합니다.
        
        Args:
            query (str): 검색 질의
            k (int): 반환할 문서 수 (기본값: 3)
            
        Returns:
            List[Dict[str, Any]]: 검색 결과 리스트
        """
        try:
            # RAG 엔진 초기화 확인
            if self.vector_store is None:
                self.initialize()
            
            # [Similarity Search] 유사도 기반 문서 검색
            docs = self.vector_store.similarity_search(query, k=k)
            
            # [Result Formatting] 검색 결과를 구조화된 형태로 변환
            results = []
            for doc in docs:
                result = {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "알 수 없음"),
                    "category": doc.metadata.get("category", "일반"),
                    "doc_type": doc.metadata.get("doc_type", "unknown")
                }
                results.append(result)
            
            self.logger.info(f"[Knowledge Search] '{query}' 검색 완료 - {len(results)}건 결과")
            return results
            
        except Exception as e:
            self.logger.error(f"[Knowledge Search] 검색 실패: {e}")
            # [Error Handling] 검색 실패 시에도 빈 결과 반환 (시스템 안정성)
            return []
    
    def get_search_summary(self, query: str, k: int = 3) -> str:
        """
        [Search Summary] 검색 결과 요약
        
        에이전트가 사용하기 쉽도록 검색 결과를 텍스트로 요약합니다.
        출처 정보를 포함하여 정보의 신뢰성을 보장합니다.
        
        Args:
            query (str): 검색 질의
            k (int): 검색할 문서 수
            
        Returns:
            str: 요약된 검색 결과
        """
        results = self.search(query, k)
        
        if not results:
            return "[사내 지식베이스] 관련 정보를 찾을 수 없습니다."
        
        # [Summary Formatting] 출처와 함께 결과 요약
        summary_parts = []
        for i, result in enumerate(results, 1):
            summary_parts.append(
                f"[출처: {result['source']}] {result['content']}"
            )
        
        summary = "\n\n".join(summary_parts)
        
        # [Compliance Notice] 금융 규제 준수를 위한 면책 조항
        disclaimer = "\n\n※ 본 정보는 사내 데이터베이스 기반이며, 투자 결정 시 최신 정보를 별도 확인하시기 바랍니다."
        
        return summary + disclaimer


# [Global Instance] 전역 RAG 엔진 인스턴스
# 싱글톤 패턴으로 구현되어 앱 전체에서 하나의 인스턴스만 사용됩니다.
rag_engine = RAGEngine()