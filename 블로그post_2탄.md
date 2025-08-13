# 코페르니쿠스 해양 데이터 분석 자동화 시스템 개발기 2탄
## 진짜 다운로드가 되는 스크래퍼 만들기

## 1탄 정정과 실제 도전 과제

1탄에서 시스템이 완벽히 완성된 것처럼 썼지만, 사실 절반의 성공이었다. 링크는 수집했지만 실제 파일 다운로드는 쉽지 않았다. 이번 2탄에서는 **실제로 작동하는** 다운로드 시스템을 만든 과정을 공유한다.

### 초기 문제: 링크는 있는데 파일이 없다

```python
# 1탄의 스크래퍼 결과
발견된 링크: 54개
실제 다운로드 가능: 0개  # 😱
```

문제는 단순했다. Copernicus 웹사이트에서 찾은 링크들이 대부분:
- JavaScript로 동적 생성되는 콘텐츠
- 로그인이 필요한 리소스
- 외부 플랫폼(GitHub, Zenodo)으로 리다이렉트
- HTML 페이지만 반환하는 잘못된 URL

## 실제 작동하는 스크래퍼 개발 과정

### Step 1: 소스를 다시 찾자

Copernicus 웹사이트만 고집하지 말고, 실제 데이터가 있는 곳을 찾기로 했다:

```python
# smart_scraper.py - 다중 소스 전략
class SmartCopernicusScraper:
    def __init__(self):
        self.sources = {
            'github': self.find_github_notebooks,
            'zenodo': self.find_zenodo_resources,
            'copernicus': self.find_direct_downloads
        }
```

### Step 2: GitHub API 활용

가장 먼저 성공한 곳은 GitHub였다. API를 사용하니 확실히 파일을 찾을 수 있었다:

```python
def find_github_notebooks(self):
    """GitHub에서 Copernicus 관련 노트북 찾기"""
    
    # GitHub API 사용
    api_url = "https://api.github.com/search/code"
    params = {
        'q': 'copernicus marine filename:*.ipynb',
        'per_page': 10
    }
    
    response = self.session.get(api_url, params=params)
    
    # 결과: euroargodev/argopy 저장소에서 4개 노트북 발견!
    # BGC_data_mode_census.ipynb
    # BGC_region_float_data.ipynb
    # ...
```

**핵심 발견**: GitHub URL을 Raw URL로 변환해야 다운로드 가능

```python
def convert_to_raw_url(github_url):
    """GitHub 뷰어 URL을 다운로드 가능한 Raw URL로 변환"""
    # 변환 전: https://github.com/user/repo/blob/main/file.ipynb
    # 변환 후: https://raw.githubusercontent.com/user/repo/main/file.ipynb
    
    raw_url = github_url.replace('github.com', 'raw.githubusercontent.com')
    raw_url = raw_url.replace('/blob/', '/')
    return raw_url
```

### Step 3: Zenodo - 학술 데이터의 보물창고

Zenodo는 학술 데이터 공유 플랫폼으로, Copernicus 관련 데이터셋이 많았다:

```python
def find_zenodo_resources(self):
    """Zenodo에서 Copernicus 데이터셋 찾기"""
    
    zenodo_api = "https://zenodo.org/api/records"
    params = {
        'q': 'copernicus marine',
        'size': 10,
        'type': 'dataset'
    }
    
    response = self.session.get(zenodo_api, params=params)
    
    # 결과: 3개 ZIP 파일 발견!
    # rms_sla.zip (32KB) - MedFS 검증 데이터
    # tracmass_3d_output.zip (6GB) - 궤적 데이터
    # CMEMS_3dre.zip (258MB) - 3D 재분석 데이터
```

### Step 4: 실제 다운로드 구현

파일을 찾는 것과 다운로드하는 것은 다른 문제였다:

```python
def download_resources(self, resources, max_files=5):
    """실제 파일 다운로드"""
    
    # 크기 기준 정렬 (작은 파일부터)
    resources_sorted = sorted(resources, key=lambda x: x.get('size', 0))
    
    for resource in resources_sorted[:max_files]:
        filename = resource.get('filename')
        url = resource.get('url')
        
        # 이미 존재하면 스킵
        if filepath.exists():
            print(f"⚠ 이미 존재: {filename}")
            continue
            
        try:
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 스트리밍 다운로드 (메모리 효율)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            print(f"✓ 완료: {filepath.stat().st_size / 1024:.1f} KB")
            
        except Exception as e:
            print(f"✗ 실패: {str(e)}")
```

## 실제 테스트 결과

### 성공한 다운로드들

```python
# 테스트 실행 결과
============================================================
Smart Copernicus Scraper
============================================================

1. GitHub 저장소 검색...
  체크: euroargodev/argopy
    ✓ 4 노트북 발견

2. Copernicus 웹사이트 스캔...
    ✓ 0 링크 발견  # 😅 역시 직접 다운로드는 어렵다

3. Zenodo 데이터셋 검색...
    ✓ 3 파일 발견

다운로드 결과:
- BGC_data_mode_census.ipynb (56KB) ✓
- BGC_region_float_data.ipynb (6.3MB) ✓  
- BGC_scatter_map_data_mode.ipynb (256KB) ✓
- rms_sla.zip (33KB) ✓

총 다운로드: 6.7MB
```

### 다운로드 기준과 제한

실무에서 사용 가능한 합리적인 제한을 설정했다:

```python
# 다운로드 정책
다운로드_기준 = {
    '파일_형식': ['.ipynb', '.zip', '.nc'],
    '최대_크기': '10MB',  # 테스트용
    '최대_개수': 5,        # API 제한 고려
    '타임아웃': 30,        # 초
    '우선순위': '크기_작은_순'
}
```

## 병렬 다운로드와 캐시 시스템 구현

### ThreadPoolExecutor로 5배 빠르게

단순 다운로드를 넘어 성능 최적화도 구현했다:

```python
# scrape_copernicus_enhanced.py
class ParallelDownloader:
    def __init__(self, max_workers=5, cache_manager=None):
        self.max_workers = max_workers
        self.cache_manager = cache_manager
        
    def download_batch(self, download_tasks):
        """병렬 배치 다운로드"""
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.download_file, url, path): (url, path)
                for url, path in download_tasks
            }
            
            # 진행 표시와 함께 결과 수집
            with tqdm(total=len(download_tasks), desc="병렬 다운로드") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    pbar.update(1)
```

### 지능형 캐시 시스템

중복 다운로드를 방지하는 캐시 시스템:

```python
class CacheManager:
    def __init__(self, cache_dir, expire_days=30):
        self.cache_dir = cache_dir
        self.expire_days = expire_days
        self.index = self._load_index()
        
    def is_cached(self, url):
        """캐시 존재 및 만료 확인"""
        cache_key = hashlib.md5(url.encode()).hexdigest()
        
        if cache_key in self.index:
            cached_date = datetime.fromisoformat(self.index[cache_key]['date'])
            if datetime.now() - cached_date < timedelta(days=self.expire_days):
                return True
                
        return False
```

## 고급 해양학 시각화 추가

데이터를 다운로드했으니 분석도 업그레이드했다:

```python
# oceanographic_visualizations.py
def plot_ts_diagram(temperature, salinity, depth=None):
    """Temperature-Salinity Diagram"""
    # 해수 밀도 계산
    density = calculate_density_simple(temperature, salinity)
    
    # 등밀도선 그리기
    cs = ax.contour(sal_mesh, temp_mesh, density, levels=15)
    ax.clabel(cs, inline=True, fontsize=8)
    
def plot_hovmoller(data, x_dim='time', y_dim='depth'):
    """Hovmöller Diagram - 시간-공간 변화"""
    im = ax.pcolormesh(data[x_dim], data[y_dim], data)
    
    if 'depth' in y_dim:
        ax.invert_yaxis()  # 깊이는 아래로
```

## 핵심 교훈

### 1. 실제 데이터 소스를 찾아라

Copernicus 웹사이트 → GitHub/Zenodo가 진짜 소스였다:
- GitHub: 코드와 노트북
- Zenodo: 검증된 데이터셋
- 웹사이트: 메타데이터와 링크만

### 2. API를 활용하라

웹 스크래핑보다 API가 확실하다:
- GitHub API: 구조화된 응답
- Zenodo API: 메타데이터 포함
- 직접 스크래핑: 불안정하고 느림

### 3. 합리적인 제한을 두어라

모든 것을 다운로드할 필요는 없다:
- 작은 파일부터 테스트
- 캐시로 중복 방지
- 병렬 처리로 속도 향상

### 4. URL 변환이 핵심이다

```python
# 이것만 알아도 절반은 성공
GitHub 뷰어 URL → Raw URL
Zenodo 레코드 → 파일 직접 링크
상대 경로 → 절대 경로
```

## 최종 성과

### 실제 작동하는 시스템

```python
✅ 찾은 리소스: 7개 (4 노트북 + 3 ZIP)
✅ 다운로드 성공: 4개 파일
✅ 총 크기: 6.7MB
✅ 소요 시간: 15초 (병렬 처리)
```

### 개선된 기능들

1탄 이후 추가된 실제 기능:
- **멀티 소스 지원**: GitHub, Zenodo, 웹사이트
- **병렬 다운로드**: 5배 속도 향상
- **캐시 시스템**: 30일 만료, MD5 기반
- **고급 시각화**: T-S 다이어그램, Hovmöller 플롯 등 9종
- **스마트 필터링**: 크기/형식/키워드 기반

## 다음 단계

아직 갈 길이 남았다:

1. **인증 처리**: Copernicus 로그인 필요 리소스
2. **대용량 파일**: 6GB 파일 처리 전략
3. **실시간 스트리밍**: 스트리밍 데이터 지원
4. **웹 인터페이스**: CLI를 넘어 웹 대시보드

## 마무리

완벽한 시스템을 한 번에 만들려 하지 말자. **작동하는 최소 기능**부터 시작해서 점진적으로 개선하는 것이 핵심이다.

1탄에서는 "링크를 찾았다"고 자랑했지만, 2탄에서야 "실제로 다운로드된다"고 말할 수 있게 되었다. 

**진짜 성과**:
- 실제 다운로드 가능한 파일 확보 ✓
- 다중 소스 전략으로 성공률 향상 ✓
- 병렬 처리와 캐시로 실용성 확보 ✓

GitHub 저장소: [copernicus-marine-toolkit](https://github.com/LimJih00n/copernicus-marine-toolkit)

다음 3탄에서는 다운로드한 데이터로 실제 해양 분석을 수행하는 과정을 다룰 예정이다. 6.3MB 노트북에 뭐가 들어있는지 궁금하지 않은가?