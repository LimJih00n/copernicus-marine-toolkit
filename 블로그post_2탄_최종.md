# 코페르니쿠스 해양 데이터 분석 자동화 시스템 개발기 2탄

## 1탄 이후

1탄에서 54개 링크 중 2개만 다운로드에 성공했다. Copernicus 웹사이트 직접 크롤링은 한계가 있었다. 접근 방법을 바꿨다.

## 소스 전략 변경

### 다중 소스 접근

Copernicus 웹사이트만 고집하지 않기로 했다. 실제 데이터가 있는 곳을 찾았다.

```python
class SmartCopernicusScraper:
    def __init__(self):
        self.sources = {
            'github': self.find_github_notebooks,
            'zenodo': self.find_zenodo_resources,
            'copernicus': self.find_direct_downloads
        }
```

### GitHub API 활용

GitHub에 공개된 노트북을 찾았다.

```python
def find_github_notebooks(self):
    api_url = "https://api.github.com/search/code"
    params = {
        'q': 'copernicus marine filename:*.ipynb',
        'per_page': 10
    }
    
    response = self.session.get(api_url, params=params)
    items = response.json().get('items', [])
    
    # 결과: euroargodev/argopy에서 4개 노트북 발견
    # BGC_data_mode_census.ipynb (56KB)
    # BGC_region_float_data.ipynb (6.3MB)
    # BGC_scatter_map_data_mode.ipynb (256KB)
```

핵심은 URL 변환이다.

```python
def convert_to_raw_url(github_url):
    # 변환 전: github.com/user/repo/blob/main/file.ipynb
    # 변환 후: raw.githubusercontent.com/user/repo/main/file.ipynb
    
    raw_url = github_url.replace('github.com', 'raw.githubusercontent.com')
    raw_url = raw_url.replace('/blob/', '/')
    return raw_url
```

### Zenodo 활용

Zenodo는 학술 데이터 저장소다. API가 잘 되어 있다.

```python
def find_zenodo_resources(self):
    zenodo_api = "https://zenodo.org/api/records"
    params = {
        'q': 'copernicus marine',
        'size': 10,
        'type': 'dataset'
    }
    
    response = self.session.get(zenodo_api, params=params)
    
    # 결과: 3개 ZIP 파일 발견
    # rms_sla.zip (32KB)
    # tracmass_3d_output.zip (6GB)
    # CMEMS_3dre.zip (258MB)
```

## 실제 다운로드 구현

### 크기 기반 전략

작은 파일부터 다운로드한다. 테스트와 개발에 효율적이다.

```python
def download_resources(self, resources, max_files=5):
    # 크기순 정렬
    resources_sorted = sorted(resources, key=lambda x: x.get('size', 0))
    
    for resource in resources_sorted[:max_files]:
        if filepath.exists():
            continue  # 이미 존재하면 스킵
            
        response = session.get(url, stream=True, timeout=30)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
```

### 실제 결과

```
Smart Copernicus Scraper
========================

1. GitHub 저장소 검색...
   ✓ 4 노트북 발견

2. Zenodo 데이터셋 검색...
   ✓ 3 파일 발견

다운로드 완료:
- BGC_data_mode_census.ipynb (56KB)
- BGC_region_float_data.ipynb (6.3MB)
- BGC_scatter_map_data_mode.ipynb (256KB)
- rms_sla.zip (33KB)

총: 6.7MB
```

1탄의 3.7% 성공률이 57%로 올랐다.

## 성능 개선

### 병렬 다운로드

ThreadPoolExecutor로 동시 다운로드를 구현했다.

```python
class ParallelDownloader:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        
    def download_batch(self, tasks):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.download_file, url, path): (url, path)
                for url, path in tasks
            }
            
            for future in as_completed(futures):
                result = future.result()
                # 진행 상황 업데이트
```

5배 속도 향상을 달성했다.

### 캐시 시스템

중복 다운로드를 방지한다.

```python
class CacheManager:
    def __init__(self, cache_dir, expire_days=30):
        self.cache_dir = cache_dir
        self.expire_days = expire_days
        
    def is_cached(self, url):
        cache_key = hashlib.md5(url.encode()).hexdigest()
        
        if cache_key in self.index:
            cached_date = datetime.fromisoformat(self.index[cache_key]['date'])
            if datetime.now() - cached_date < timedelta(days=self.expire_days):
                return True
        
        return False
```

## 고급 시각화 추가

다운로드한 데이터를 분석할 도구도 개선했다.

```python
# oceanographic_visualizations.py

def plot_ts_diagram(temperature, salinity, depth=None):
    """T-S 다이어그램"""
    density = calculate_density_simple(temperature, salinity)
    
    cs = ax.contour(sal_mesh, temp_mesh, density, levels=15)
    ax.clabel(cs, inline=True, fontsize=8)
    
def plot_hovmoller(data, x_dim='time', y_dim='depth'):
    """Hovmöller 다이어그램"""
    im = ax.pcolormesh(data[x_dim], data[y_dim], data)
    
    if 'depth' in y_dim:
        ax.invert_yaxis()
```

9개 해양학 전용 시각화 함수를 추가했다.

## 핵심 교훈

### API > 웹 스크래핑

- GitHub API: 구조화된 응답, 안정적
- Zenodo API: 메타데이터 포함
- 웹 스크래핑: 불안정, JavaScript 의존

### URL 변환이 핵심

```python
# 이것만 알면 절반은 성공
GitHub 뷰어 → Raw URL
Zenodo 레코드 → 직접 다운로드 링크
상대 경로 → 절대 경로
```

### 합리적 제한

- 파일 크기: 10MB 이하 우선
- 동시 다운로드: 5개 제한
- 타임아웃: 30초

## 최종 성과

```
찾은 리소스: 7개
다운로드 성공: 4개
총 크기: 6.7MB
소요 시간: 15초
```

1탄 대비:
- 성공률: 3.7% → 57%
- 속도: 5배 향상
- 실제 사용 가능 파일 확보

## 남은 과제

- 인증이 필요한 리소스 처리
- 대용량 파일 (6GB) 전략
- ~~더 많은 소스 추가~~ → 3탄에서 해결

코드: [GitHub](https://github.com/LimJih00n/copernicus-marine-toolkit)

작동하는 최소 기능부터 시작해서 점진적으로 개선하는 것이 핵심이다.

실제 Copernicus 사이트에서 직접 다운로드가 어려웠다. 하지만 포기하지 않았다. 3탄에서 진짜 해결책을 찾았다.