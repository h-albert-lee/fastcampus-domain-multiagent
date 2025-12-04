# 🏦 Quant-X: 교육용 금융 엔터프라이즈 AI 에이전트 시스템

> **Fastcampus 금융 AI Agent 구축 튜토리얼을 위한 멀티에이전트 투자 딥리서치 시스템**

## 📋 프로젝트 개요

Quant-X는 금융권의 엄격한 보안 규제와 시스템 통제(Governance)를 준수하는 **교육용 AI 에이전트 시스템**입니다. 단순한 챗봇이 아닌, 실제 금융 기관에서 사용하기 위한 교육적 목적 수준의 보안성과 규제 준수 기능을 갖춘 시스템입니다.

### 🎯 핵심 철학
**"AI는 시스템의 통제 하에, 인가된 데이터와 도구만 사용할 수 있다."**

### 🏗️ 아키텍처
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Governance    │    │   Execution     │
│   (Streamlit)   │◄──►│   (Security)    │◄──►│   (AI Agent)    │
│                 │    │                 │    │                 │
│ • 사용자 UI     │    │ • 인증/권한     │    │ • smolagents    │
│ • 관리자 대시보드│    │ • 감사 로그     │    │ • 도구 실행     │
│ • 리서치 포털   │    │ • 보안 필터링   │    │ • RAG 검색      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 주요 기능

### 🔐 보안 & 거버넌스
- **역할 기반 접근 제어 (RBAC)**: Junior/Senior 권한 분리
- **실시간 감사 로그**: 모든 AI 행위 추적 및 기록
- **보안 가드레일**: 입력/출력 필터링 및 규제 준수
- **투명한 미들웨어**: 에이전트 모르게 모든 도구 호출 감시

### 🧠 AI 에이전트
- **smolagents CodeAgent**: Python 코드 생성을 통한 논리적 추론
- **금융 도메인 특화**: 주가 분석, 시장 동향, 투자 리서치
- **사내 지식베이스 우선**: RAG를 통한 내부 데이터 활용
- **다중 도구 통합**: 웹 검색, 주가 조회, 리포트 생성

### 📊 지식 관리
- **HuggingFace 데이터셋**: 한국어 금융 공시 및 리포트 데이터
- **FAISS 벡터 검색**: 고속 유사도 검색 엔진
- **캐싱 전략**: 초기 로딩 후 로컬 저장으로 성능 최적화

## 🛠️ 기술 스택

| 계층 | 기술 | 역할 |
|------|------|------|
| **Frontend** | Streamlit | 사내 리서치 포털 UI |
| **Governance** | Python | 권한 체크, 감사 로그, 가드레일 |
| **Brain** | smolagents | CodeAgent 기반 AI 추론 |
| **Knowledge** | LangChain + FAISS | HuggingFace 금융 데이터 RAG |
| **Data** | HuggingFace Datasets | 한국어 금융 공시/리포트 |

## 📁 프로젝트 구조

```
QuantX_Project/
├── 📄 app.py                    # Streamlit 메인 실행 파일
├── 📄 requirements.txt          # 패키지 의존성
├── 📄 .env                      # API 키 설정 (OpenAI, HuggingFace 등)
├── 📄 .gitignore               # Git 제외 파일
│
├── 📁 core/                     # 거버넌스 레이어
│   ├── 🔐 auth.py              # 사용자 인증 및 권한 관리
│   ├── 🛡️ guardrails.py        # 보안 필터링 및 규제 준수
│   ├── 📋 logger.py            # 감사 로그 시스템
│   └── 🧠 rag_engine.py        # 지식베이스 검색 엔진
│
├── 📁 agents/                   # 실행 레이어
│   ├── 🤖 core.py              # AI 에이전트 코어 로직
│   └── 🛠️ tools.py             # 도구 함수 (미들웨어 패턴)
│
└── 📁 data/                     # 데이터 저장소
    ├── 📁 reports/             # 생성된 리포트
    └── 📁 vector_store/        # FAISS 벡터 인덱스
```

## 🚀 설치 및 실행

### 1. 환경 설정
```bash
# 프로젝트 클론
git clone https://github.com/h-albert-lee/fastcampus-domain-multiagent.git
cd fastcampus-domain-multiagent/QuantX_Project

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정 (선택사항)
# .env 파일 생성 후 API 키 입력
```

### 2. 필수 API 키 설정 (선택사항)
```bash
# .env 파일 내용 (실제 AI 기능 사용 시)
OPENAI_API_KEY=your_openai_api_key_here
HUGGINGFACE_API_TOKEN=your_huggingface_token_here  # 선택사항
SERPER_API_KEY=your_serper_api_key_here           # 웹 검색용
```

### 3. 애플리케이션 실행
```bash
# QuantX_Project 폴더에서 실행
cd QuantX_Project
streamlit run app.py
```

### 4. 데모 모드 (API 키 없이 실행)
API 키가 없어도 교육 목적으로 데모 모드로 실행 가능합니다.

## 👥 사용자 역할

### 🔰 Junior Analyst (`analyst_*`)
- ✅ 사내 데이터 검색
- ✅ 웹 검색
- ✅ 주가 조회
- ❌ 리포트 저장 불가
- ❌ 민감 데이터 접근 불가

### 👑 Senior Manager (`senior_*`)
- ✅ 모든 Junior 권한
- ✅ 리포트 저장
- ✅ 민감 데이터 접근
- ✅ 관리자 대시보드 접근

## 📊 관리자 대시보드

### 📈 시스템 통계
- 총 로그 수, 사용자 활동, 시스템 이벤트 현황
- 사용자별 활동 통계 차트

### 🔒 보안 현황
- 보안 이벤트 모니터링
- 위험 수준별 분류 및 대응 현황

### 📋 감사 로그
- 실시간 사용자 활동 추적
- 상세 로그 검색 및 필터링
- CSV 다운로드 지원

## 🎓 교육적 특징

### 💡 풍부한 주석
모든 코드에 **"왜(Why) 금융 도메인에서 이런 처리가 필요한지"**를 설명하는 교육용 주석 포함

### 🏗️ 명확한 계층 분리
- **UI Layer**: 사용자 인터페이스
- **Governance Layer**: 보안 및 규제 준수
- **Execution Layer**: AI 에이전트 실행

### 🛡️ 실패에 강한 설계
- API 호출 실패 시 graceful degradation
- 에러 상황에서도 시스템 안정성 유지

## 🔧 주요 도구

| 도구명 | 기능 | 권한 요구사항 |
|--------|------|---------------|
| `search_internal` | 사내 지식베이스 검색 | 모든 사용자 |
| `search_web` | 웹 검색 (Serper API) | 모든 사용자 |
| `get_stock_price` | 실시간 주가 조회 | 모든 사용자 |
| `save_report` | 분석 리포트 저장 | Senior만 가능 |
| `get_market_summary` | 시장 현황 요약 | 모든 사용자 |

## 📝 사용 예시

### 기본 리서치 요청
```
삼성전자의 최근 주가 동향과 실적을 분석해주세요.
```

### 시장 분석 요청
```
현재 코스피 상황과 주요 섹터별 동향을 정리해주세요.
```

### 사내 데이터 검색
```
반도체 관련 최근 공시 내용을 찾아서 요약해주세요.
```

## ⚠️ 주의사항

### 🔒 보안
- 모든 사용자 활동이 감사 로그에 기록됩니다
- 보안 정책 위반 시 요청이 차단됩니다
- 민감한 정보는 적절한 권한이 있는 사용자만 접근 가능합니다

### 💼 규제 준수
- 본 시스템은 교육용으로 제작되었습니다
- 실제 투자 결정에 사용하지 마세요
- 모든 정보는 참고용이며, 투자 책임은 본인에게 있습니다

### 🔧 기술적 제한
- OpenAI API 키가 필요합니다 (데모 모드 제외)
- 인터넷 연결이 필요합니다 (웹 검색, 주가 조회)
- 초기 실행 시 HuggingFace 데이터셋 다운로드로 시간이 소요될 수 있습니다

## 🤝 기여하기

이 프로젝트는 Fastcampus 교육용으로 제작되었습니다. 개선 사항이나 버그 리포트는 이슈로 등록해 주세요.

## 📄 라이선스

이 프로젝트는 교육 목적으로 제작되었으며, MIT 라이선스 하에 배포됩니다.

---

**🏦 Quant-X Financial Research Portal**  
*금융 엔터프라이즈 AI 에이전트 시스템 | 교육용 데모 버전*

Made with ❤️ for Fastcampus
