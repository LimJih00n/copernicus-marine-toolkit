# 코페르니쿠스 해양 데이터 분석 자동화 시스템 개발기 1탄

## 배경

해양 데이터 분석에서 반복되는 작업이 많다. Copernicus Marine Service에서 데이터를 받고, 전처리하고, 분석하는 과정이 프로젝트마다 비슷하다. 이를 자동화하는 시스템을 만들기로 했다.

목표는 세 가지다:
- Copernicus 튜토리얼 자동 수집
- 공통 분석 패턴을 함수로 모듈화
- 재사용 가능한 템플릿 제공

## 웹 크롤링 시도

### 첫 접근

BeautifulSoup으로 시작했다.

```python
import requests
from bs4 import BeautifulSoup

def scrape_tutorials():
    url = "https://marine.copernicus.eu/services/user-learning-services/tutorials"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = soup.find_all('a', href=True)
    tutorial_links = [l['href'] for l in links if 'tutorial' in l['href']]
    
    return tutorial_links
```

12개 링크를 찾았다. 하지만 대부분 HTML 페이지였다. 실제 파일은 없었다.

### JavaScript 문제

페이지를 확인해보니 JavaScript로 콘텐츠가 생성되고 있었다. Selenium을 도입했다.

```python
from selenium import webdriver

class CoperniciusScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
        
    def scrape_with_js(self):
        self.driver.get(self.base_url)
        time.sleep(3)  # JS 로딩 대기
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        return self.extract_links(soup)
```

54개로 늘었다. 진전이 있었다.

## 다운로드 검증

링크를 찾는 것과 다운로드는 별개 문제였다.

```python
def test_download(url):
    response = requests.get(url, timeout=10)
    content_type = response.headers.get('content-type', '')
    
    if 'html' in content_type:
        return "HTML 페이지"
    elif 'zip' in content_type:
        return "ZIP 파일"
    else:
        # 파일 헤더 확인
        header = response.content[:8]
        if b'PK' in header:
            return "ZIP"
        elif b'CDF' in header:
            return "NetCDF"
    
    return "알 수 없음"

# 결과
# 총 54개 중:
# - 실제 파일: 2개
# - HTML 페이지: 48개
# - 접근 불가: 4개
```

54개 중 2개만 다운로드 가능했다. 대부분이 다른 사이트로의 링크거나 로그인이 필요했다.

## 분석 함수 개발

다운로드는 나중에 해결하기로 하고, 분석 함수를 먼저 만들었다.

### 기본 함수

```python
# copernicus_utils.py

def load_dataset(filepath, chunks=None):
    """NetCDF 로딩"""
    return xr.open_dataset(filepath, chunks=chunks)

def subset_region(ds, lon_range, lat_range):
    """지역 추출"""
    # 차원 이름 자동 인식
    lon_names = ['longitude', 'lon', 'x']
    lat_names = ['latitude', 'lat', 'y']
    
    lon_dim = next((n for n in lon_names if n in ds.dims), None)
    lat_dim = next((n for n in lat_names if n in ds.dims), None)
    
    return ds.sel({
        lon_dim: slice(lon_range[0], lon_range[1]),
        lat_dim: slice(lat_range[0], lat_range[1])
    })
```

차원 이름이 데이터셋마다 다른 문제를 해결했다.

### 해양학 특화 함수

```python
def calculate_spatial_mean(data, lat_weighted=True):
    """위도 가중 평균"""
    if lat_weighted:
        weights = np.cos(np.deg2rad(data.latitude))
        return data.weighted(weights).mean(dim=['longitude', 'latitude'])
    
    return data.mean(dim=['longitude', 'latitude'])

def detect_marine_heatwaves(sst_data, threshold_percentile=90):
    """해양열파 감지 - 미완성"""
    # TODO: 5일 연속 조건 구현 필요
    threshold = sst_data.quantile(threshold_percentile/100, dim='time')
    return sst_data > threshold
```

20개 함수를 구현했다. 일부는 아직 미완성이다.

## 테스트

```python
import unittest

class TestCopernicusUtils(unittest.TestCase):
    def setUp(self):
        # 테스트용 가짜 데이터
        self.test_data = xr.DataArray(
            np.random.randn(10, 20, 30),
            dims=['time', 'latitude', 'longitude']
        )
    
    def test_subset_region(self):
        subset = cu.subset_region(self.test_data.to_dataset(name='test'),
                                 lon_range=(125, 135),
                                 lat_range=(35, 40))
        
        assert subset.longitude.min() >= 125
        assert subset.longitude.max() <= 135
```

기본 기능은 동작한다. 실제 데이터로는 아직 테스트하지 못했다.

## 현재 상태

### 완료
- Selenium 기반 크롤러
- 20개 분석 함수
- 기본 테스트

### 미완료
- 실제 파일 다운로드 (2/54개만 성공)
- 해양열파 감지 함수
- 실제 데이터 테스트

### 문제점
- Copernicus 직접 다운로드 어려움
- 대부분 외부 사이트 링크
- 로그인 필요한 리소스 처리 못함

## 다음 단계

1탄에서는 기본 구조를 만들었다. 하지만 핵심인 다운로드가 작동하지 않는다.

2탄에서 해결할 문제:
- GitHub, Zenodo 등 실제 데이터 소스 활용
- API 기반 접근
- 병렬 다운로드

코드: [GitHub](https://github.com/LimJih00n/copernicus-marine-toolkit)

현재 성공률: 3.7% (2/54)