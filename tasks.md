# 코페르니쿠스 해양 연구 분석 시스템 개발 작업 계획

## 프로젝트 개요
코페르니쿠스 해양 서비스의 튜토리얼을 자동 수집하고 모듈화하여 재사용 가능한 분석 시스템 구축

## 작업 단계

### Phase 1: 프로젝트 초기 설정 ✅
- [x] 프로젝트 폴더 구조 설계
- [x] 필요 라이브러리 목록 작성
- [x] tasks.md 작성

### Phase 2: 자동 수집 시스템 개발 (Epic 1) 🎯

#### 2.1 웹 크롤러 개발
- [ ] 코페르니쿠스 튜토리얼 페이지 구조 분석
  - URL: https://marine.copernicus.eu/services/user-learning-services/tutorials
  - 페이지 HTML 구조 파악
  - 튜토리얼 링크 패턴 식별
- [ ] BeautifulSoup을 활용한 크롤러 구현
  - 메인 페이지에서 튜토리얼 목록 추출
  - 각 튜토리얼 상세 페이지 URL 수집
- [ ] 다운로드 가능한 리소스 식별
  - .ipynb 파일 링크 추출
  - 관련 데이터 파일(.nc, .csv) 링크 추출

#### 2.2 다운로드 스크립트 개발
- [ ] `scrape_copernicus.py` 메인 스크립트 작성
  - 명령줄 인터페이스 구현
  - 다운로드 진행 상황 표시
  - 에러 핸들링 및 재시도 로직
- [ ] 파일 다운로드 기능 구현
  - requests 라이브러리 활용
  - 대용량 파일 스트리밍 다운로드
  - 중복 다운로드 방지

#### 2.3 자동 폴더 구조 생성
- [ ] 튜토리얼별 폴더 자동 생성
  - 폴더명 정규화 (특수문자 제거)
  - 계층적 폴더 구조 구현
- [ ] 다운로드 메타데이터 저장
  - 다운로드 날짜, 원본 URL 등 기록
  - JSON 형식으로 저장

### Phase 3: 코드 모듈화 (Epic 2) 🧩

#### 3.1 노트북 분석 및 패턴 식별
- [ ] 수집된 노트북 자동 파싱
  - nbformat 라이브러리 활용
  - 코드 셀 추출 및 분석
- [ ] 공통 패턴 식별
  - 데이터 로딩 패턴
  - 전처리 패턴
  - 시각화 패턴
- [ ] 함수 추출 대상 목록 작성

#### 3.2 유틸리티 모듈 개발
- [ ] `copernicus_utils.py` 파일 생성
- [ ] 핵심 기능 함수 구현 (최소 10개)
  - `load_dataset()`: NetCDF 데이터 로딩
  - `subset_region()`: 지역별 데이터 추출
  - `subset_time()`: 시간대별 데이터 추출
  - `calculate_spatial_mean()`: 공간 평균 계산
  - `create_timeseries()`: 시계열 데이터 생성
  - `plot_map()`: 지도 시각화
  - `plot_timeseries()`: 시계열 그래프
  - `export_to_csv()`: CSV 내보내기
  - `calculate_anomaly()`: 이상치 계산
  - `apply_moving_average()`: 이동평균 적용
- [ ] 함수별 docstring 작성
- [ ] 단위 테스트 작성

### Phase 4: 맞춤형 분석 환경 구축 (Epic 3) 🔬

#### 4.1 템플릿 노트북 개발
- [ ] `template_analysis.ipynb` 작성
  - 표준 라이브러리 import
  - 분석 단계별 섹션 구성
  - 사용 예시 포함
- [ ] README 작성
  - 템플릿 사용 방법
  - 함수 사용 가이드

#### 4.2 실제 분석 예시 작성
- [ ] 예시 1: 동해 SST 장기 변화 분석
  - 여러 데이터셋 조합
  - 시계열 및 공간 분석
  - 트렌드 분석
- [ ] 예시 2: 엘니뇨가 한반도 해역에 미치는 영향
  - 상관관계 분석
  - 지연 상관 분석
  - 복합 시각화

### Phase 5: 테스트 및 문서화 📚

#### 5.1 통합 테스트
- [ ] 전체 파이프라인 테스트
  - 크롤링 → 다운로드 → 모듈화 → 분석
- [ ] 성능 측정
  - 기존 방식 대비 시간 단축 측정
  - 메모리 사용량 최적화

#### 5.2 문서화
- [ ] 설치 가이드 작성
- [ ] API 문서 생성
- [ ] 사용자 매뉴얼 작성
- [ ] 트러블슈팅 가이드

## 프로젝트 구조
```
marine_model_collector/
├── scrape_copernicus.py      # 메인 크롤링 스크립트
├── copernicus_utils.py        # 재사용 가능한 함수 모음
├── requirements.txt           # 필요 라이브러리
├── tasks.md                   # 작업 계획 (현재 파일)
├── README.md                  # 프로젝트 설명서
├── tutorials/                 # 다운로드된 튜토리얼 저장
│   ├── 01_tutorial_name/
│   ├── 02_tutorial_name/
│   └── ...
├── notebooks/                 # 맞춤형 분석 노트북
│   ├── template_analysis.ipynb
│   ├── example_01_sst_analysis.ipynb
│   └── example_02_elnino_impact.ipynb
├── tests/                     # 테스트 코드
│   └── test_utils.py
└── docs/                      # 문서화
    ├── installation.md
    └── user_guide.md
```

## 필요 라이브러리
```
requests
beautifulsoup4
pandas
numpy
xarray
netCDF4
matplotlib
cartopy
jupyter
nbformat
tqdm
pytest
```

## 예상 일정
- Phase 1: 0.5일 ✅
- Phase 2: 2일
- Phase 3: 2일
- Phase 4: 1.5일
- Phase 5: 1일
**총 예상 기간: 7일**

## 성공 지표
- ✅ 튜토리얼 95% 이상 자동 수집
- ✅ 10개 이상 핵심 기능 모듈화
- ✅ 분석 시간 50% 단축