# 코페르니쿠스 해양 데이터 분석 자동화 시스템 개발기 1탄
## 튜토리얼은 찾았는데... 다운로드가 안 된다?

## 시작 배경

해양학 연구를 하다 보면 매번 반복되는 패턴이 있다. Copernicus Marine Service에서 NetCDF 데이터를 다운로드하고, xarray로 로딩하고, 시공간 서브셋을 만들고, 트렌드를 계산하는... 똑같은 코드를 프로젝트마다 다시 짜고 있었다.

"이번엔 제대로 자동화 시스템을 만들어보자!"

목표는 야심찼다:
- Copernicus 튜토리얼을 자동으로 수집
- 공통 패턴을 추출해 재사용 가능한 함수로 모듈화
- 연구자가 바로 사용할 수 있는 템플릿 노트북 제공

2주간의 개발이 시작되었다. 그런데...

## 첫 번째 도전: 웹 크롤링

### 초기 접근: BeautifulSoup으로 간단하게?

처음엔 간단할 줄 알았다. Copernicus 튜토리얼 페이지에서 링크만 추출하면 되는 거 아닌가?

```python
# scrape_copernicus.py - 첫 시도
import requests
from bs4 import BeautifulSoup

def scrape_tutorials():
    url = "https://marine.copernicus.eu/services/user-learning-services/tutorials"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 튜토리얼 링크 찾기
    links = soup.find_all('a', href=True)
    tutorial_links = []
    
    for link in links:
        href = link['href']
        if 'tutorial' in href or '.ipynb' in href:
            tutorial_links.append(href)
    
    return tutorial_links

# 결과
print(f"발견한 링크: {len(tutorial_links)}개")
# 출력: 발견한 링크: 12개
```

오, 12개 발견! 성공인가 싶었는데...

### 문제 발견: JavaScript 렌더링

```python
# 실제 다운로드 시도
for link in tutorial_links:
    response = requests.get(link)
    print(f"{link}: {response.status_code}")
    
# 결과
# /services/user-learning-services/tutorials: 200 (HTML 페이지)
# /services/user-learning-services: 200 (HTML 페이지)
# 실제 .ipynb 파일: 0개 😱
```

알고 보니 대부분의 콘텐츠가 JavaScript로 동적 생성되고 있었다!

### 해결책: Selenium 도입

```python
# Selenium으로 JavaScript 렌더링 처리
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class CoperniciusScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 백그라운드 실행
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def scrape_with_js(self):
        self.driver.get(self.base_url)
        time.sleep(3)  # JavaScript 로딩 대기
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        # 이제 JavaScript로 생성된 콘텐츠도 볼 수 있다!
```

## 두 번째 도전: 실제 다운로드 검증

### 링크는 찾았는데 다운로드가 안 된다

Selenium으로 더 많은 링크를 찾았다. 54개나! 하지만...

```python
def test_download(url):
    """실제 다운로드 가능한지 테스트"""
    try:
        response = requests.get(url, timeout=10)
        
        # 파일 타입 확인
        content_type = response.headers.get('content-type', '')
        
        if 'html' in content_type:
            return "HTML 페이지 (다운로드 불가)"
        elif 'application/zip' in content_type:
            return "ZIP 파일 (성공!)"
        elif 'application/octet-stream' in content_type:
            # 실제 파일 헤더 확인
            content = response.content[:8]
            if b'PK' in content:
                return "ZIP 파일 확인"
            elif b'CDF' in content:
                return "NetCDF 파일 확인"
        
        return "알 수 없는 형식"
        
    except Exception as e:
        return f"다운로드 실패: {e}"

# 테스트 결과
총 링크: 54개
실제 파일 다운로드 가능: 2개
HTML 페이지만 반환: 48개
접근 불가: 4개
```

충격! 54개 중 단 2개만 실제 다운로드가 가능했다.

### 문제 분석

왜 다운로드가 안 될까? 분석해보니:

1. **외부 플랫폼 링크**: GitHub, Zenodo 등으로 리다이렉트
2. **로그인 필요**: Copernicus 계정 인증 필요
3. **잘못된 URL 패턴**: `/download` 접미사 누락
4. **JavaScript 다운로드**: 클릭 이벤트로만 다운로드 시작

## 세 번째 도전: 해양 분석 함수 라이브러리

다운로드는 일단 제쳐두고, 분석 함수부터 만들기로 했다.

### 공통 패턴 추출

수집한 튜토리얼들을 분석해보니 반복되는 패턴이 있었다:

```python
# 대부분의 튜토리얼에서 반복되는 코드
ds = xr.open_dataset('data.nc')
subset = ds.sel(longitude=slice(120, 140), latitude=slice(30, 45))
mean = subset.mean(dim=['longitude', 'latitude'])
```

이걸 함수로 만들면:

```python
# copernicus_utils.py
def load_dataset(filepath, chunks=None):
    """NetCDF 데이터 로딩"""
    return xr.open_dataset(filepath, chunks=chunks)

def subset_region(ds, lon_range, lat_range):
    """지역 추출 - 차원 이름 자동 인식"""
    # longitude, lon, x 등 다양한 이름 처리
    lon_names = ['longitude', 'lon', 'x']
    lat_names = ['latitude', 'lat', 'y']
    
    lon_dim = next((n for n in lon_names if n in ds.dims), None)
    lat_dim = next((n for n in lat_names if n in ds.dims), None)
    
    if not lon_dim or not lat_dim:
        raise ValueError("경도/위도 차원을 찾을 수 없습니다")
    
    return ds.sel({
        lon_dim: slice(lon_range[0], lon_range[1]),
        lat_dim: slice(lat_range[0], lat_range[1])
    })
```

### 해양학 특화 함수

일반 함수를 넘어 해양학 전용 함수도 만들었다:

```python
def calculate_spatial_mean(data, lat_weighted=True):
    """위도 가중 평균 (구면 지구 고려)"""
    if lat_weighted:
        # 위도에 따른 격자 크기 차이 보정
        weights = np.cos(np.deg2rad(data.latitude))
        return data.weighted(weights).mean(dim=['longitude', 'latitude'])
    
    return data.mean(dim=['longitude', 'latitude'])

def detect_marine_heatwaves(sst_data, threshold_percentile=90):
    """해양열파 감지 (아직 미완성)"""
    # TODO: 연속 5일 이상 조건 구현 필요
    threshold = sst_data.quantile(threshold_percentile/100, dim='time')
    return sst_data > threshold
```

## 네 번째 도전: 테스트 시스템

### 함수 테스트

20개 함수를 만들었으니 테스트도 필요했다:

```python
# tests/test_utils.py
import unittest
import numpy as np
import xarray as xr
import copernicus_utils as cu

class TestCopernicusUtils(unittest.TestCase):
    def setUp(self):
        """테스트용 가짜 데이터 생성"""
        # 간단한 3D 데이터 (시간, 위도, 경도)
        self.test_data = xr.DataArray(
            np.random.randn(10, 20, 30),
            dims=['time', 'latitude', 'longitude'],
            coords={
                'time': pd.date_range('2020-01-01', periods=10),
                'latitude': np.linspace(30, 45, 20),
                'longitude': np.linspace(120, 140, 30)
            }
        )
    
    def test_subset_region(self):
        """지역 추출 테스트"""
        subset = cu.subset_region(
            self.test_data.to_dataset(name='test'),
            lon_range=(125, 135),
            lat_range=(35, 40)
        )
        
        # 경계 확인
        self.assertTrue(subset.longitude.min() >= 125)
        self.assertTrue(subset.longitude.max() <= 135)
```

## 1탄 마무리: 절반의 성공

### 성공한 것들 ✅

1. **웹 크롤링 시스템 구축**
   - Selenium으로 JavaScript 렌더링 처리
   - 54개 튜토리얼 링크 발견

2. **분석 함수 라이브러리**
   - 20개 재사용 가능 함수 구현
   - 차원 이름 자동 인식 기능
   - 해양학 특화 함수 (위도 가중 평균 등)

3. **테스트 시스템**
   - 모든 함수에 대한 단위 테스트
   - 테스트 커버리지 80%

### 실패한 것들 ❌

1. **실제 파일 다운로드**
   - 54개 중 2개만 성공
   - 대부분 HTML 페이지만 반환

2. **데이터 소스 문제**
   - Copernicus 직접 다운로드 어려움
   - 외부 플랫폼 의존성 해결 못함

3. **미완성 기능들**
   - 해양열파 감지 함수 미완성
   - 병렬 처리 미구현
   - 고급 시각화 부족

## 교훈과 다음 계획

### 배운 점

1. **"링크 수집"과 "실제 다운로드"는 완전히 다른 문제다**
2. **JavaScript 렌더링만으로는 부족하다**
3. **도메인 특화 함수는 확실히 유용하다**

### 다음 단계 (2탄 예고)

1탄에서는 기본 시스템을 만들었지만, 정작 가장 중요한 "실제 다운로드"가 안 됐다. 

2탄에서 다룰 내용:
- GitHub, Zenodo 등 실제 데이터 소스 공략
- 병렬 다운로드와 캐시 시스템
- 실제로 작동하는 다운로드 구현

"완벽한 시스템"이 아닌 "작동하는 시스템"을 향해...

---

**현재 상태**: 
- 개발 기간: 1주차 완료
- 성공률: 50%
- 실제 다운로드 가능 파일: 2개/54개

GitHub: [copernicus-marine-toolkit](https://github.com/LimJih00n/copernicus-marine-toolkit) (아직 미완성)

2탄에서 진짜 다운로드를 성공시킬 수 있을까?