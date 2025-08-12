# 사용자 가이드

코페르니쿠스 해양 연구 분석 시스템의 상세한 사용 방법을 안내합니다.

## 목차

1. [빠른 시작](#빠른-시작)
2. [데이터 수집](#데이터-수집)
3. [분석 도구 사용법](#분석-도구-사용법)
4. [고급 사용법](#고급-사용법)
5. [문제 해결](#문제-해결)
6. [최적화 팁](#최적화-팁)

## 빠른 시작

### 1단계: 환경 준비
```bash
# 저장소 클론
git clone https://github.com/your-username/marine_model_collector.git
cd marine_model_collector

# 의존성 설치
pip install -r requirements.txt
```

### 2단계: 튜토리얼 수집
```bash
# 모든 튜토리얼 자동 다운로드
python scrape_copernicus.py
```

### 3단계: 첫 번째 분석
```bash
# Jupyter Lab 실행
jupyter lab

# notebooks/template_analysis.ipynb 열기
```

## 데이터 수집

### 기본 사용법

```bash
# 기본 설정으로 실행
python scrape_copernicus.py

# 커스텀 설정
python scrape_copernicus.py --url "https://custom-url.com" --output "my_tutorials"
```

### 고급 설정

```python
from scrape_copernicus import CopernicusScraper

# 커스텀 스크래퍼 생성
scraper = CopernicusScraper(
    base_url="https://marine.copernicus.eu/services/user-learning-services/tutorials",
    output_dir="tutorials"
)

# 실행
scraper.run()
```

### 다운로드 결과 확인

```python
import json

# 메타데이터 확인
with open('tutorials/metadata.json', 'r') as f:
    metadata = json.load(f)

print(f"다운로드된 튜토리얼: {len(metadata['tutorials'])}개")
print(f"수집 날짜: {metadata['scrape_date']}")
```

## 분석 도구 사용법

### 기본 워크플로우

```python
import copernicus_utils as cu
import matplotlib.pyplot as plt

# 1. 데이터 로딩
ds = cu.load_dataset('path/to/data.nc')

# 2. 지역/시간 추출
ds_region = cu.subset_region(ds, lon_range=(120, 140), lat_range=(30, 45))
ds_subset = cu.subset_time(ds_region, '2020-01-01', '2023-12-31')

# 3. 분석
ts = cu.create_timeseries(ds_subset, 'sst', spatial_mean=True)
trend = cu.calculate_trend(ts)

# 4. 시각화
cu.plot_timeseries(ts, title='SST Time Series')
plt.show()

print(f"온난화 트렌드: {trend['slope']*365.25:.3f}°C/year")
```

### 데이터 로딩 옵션

```python
# 기본 로딩
ds = cu.load_dataset('data.nc')

# 대용량 데이터용 청킹
ds = cu.load_dataset('large_data.nc', 
                     chunks={'time': 100, 'latitude': 50, 'longitude': 50})

# 특정 엔진 사용
ds = cu.load_dataset('data.nc', engine='h5netcdf')

# 시간 디코딩 비활성화
ds = cu.load_dataset('data.nc', decode_times=False)
```

### 지역 추출 방법

```python
# 좌표로 추출
ds_east_sea = cu.subset_region(ds, (128, 142), (35, 45))

# 다른 차원 이름 사용
ds_subset = cu.subset_region(ds, (120, 130), (30, 40), 
                            lon_dim='lon', lat_dim='lat')
```

### 시계열 분석

```python
# 공간 평균 시계열
ts_mean = cu.create_timeseries(ds, 'sst', spatial_mean=True)

# 특정 지점 시계열
ts_point = cu.create_timeseries(ds, 'sst', lon_point=130, lat_point=37)

# 위도 가중치 적용 공간 평균
ts_weighted = cu.calculate_spatial_mean(ds, 'sst', weighted=True)
```

### 트렌드 분석

```python
# 선형 트렌드
linear_trend = cu.calculate_trend(ts, method='linear')
print(f"기울기: {linear_trend['slope']}")
print(f"R²: {linear_trend['r_squared']}")
print(f"p-value: {linear_trend['p_value']}")

# Sen's slope (비모수 방법)
sen_trend = cu.calculate_trend(ts, method='sen')
print(f"Sen's slope: {sen_trend['slope']}")

# 2차 다항식 피팅
poly_trend = cu.calculate_trend(ts, method='polynomial')
```

### 이상치 분석

```python
# 기본 이상치 (전체 기간 기준)
anomaly = cu.calculate_anomaly(ds, 'sst')

# 특정 기간 기준
anomaly = cu.calculate_anomaly(ds, 'sst', 
                              reference_period=('2000-01-01', '2010-12-31'))

# 백분율 이상치
anomaly_pct = cu.calculate_anomaly(ds, 'sst', method='percentage')
```

### 극값 탐지

```python
# 95 퍼센타일 극값
extremes = cu.detect_extremes(ts, threshold_type='percentile', 
                             threshold_value=95)

# 절대값 기준
extremes = cu.detect_extremes(ts, threshold_type='absolute', 
                             threshold_value=25.0)

# 표준편차 기준
extremes = cu.detect_extremes(ts, threshold_type='std', 
                             threshold_value=2.0)

# 최소 지속기간 설정
extremes = cu.detect_extremes(ts, threshold_type='percentile',
                             threshold_value=95, duration=7)
```

### 상관관계 분석

```python
# 동시 상관관계
corr, pval = cu.calculate_correlation(ts1, ts2)

# 지연 상관관계
corr_lag3 = cu.calculate_correlation(ts1, ts2, lag=3)

# 다른 상관 방법
spearman_corr = cu.calculate_correlation(ts1, ts2, method='spearman')
kendall_corr = cu.calculate_correlation(ts1, ts2, method='kendall')
```

### 시각화

```python
# 지도 시각화
fig, ax = cu.plot_map(ds, 'sst', 
                      time_idx='2023-07-01',
                      figsize=(12, 8),
                      cmap='RdYlBu_r',
                      title='July 2023 SST')

# 시계열 플롯
fig, ax = cu.plot_timeseries(ts, 
                            title='SST Time Series',
                            ylabel='Temperature (°C)',
                            grid=True)

# 여러 시계열 플롯
ts_dict = {'Region1': ts1, 'Region2': ts2}
fig, ax = cu.plot_timeseries(ts_dict, 
                            title='Multi-region Comparison')
```

### 데이터 내보내기

```python
# CSV 내보내기
cu.export_to_csv(ts, 'timeseries.csv')

# Dataset 내보내기
cu.export_to_csv(ds, 'dataset.csv', var_names=['sst', 'salinity'])

# DataFrame 내보내기
df = pd.DataFrame({'sst': ts.values, 'date': ts.index})
cu.export_to_csv(df, 'data.csv')
```

## 고급 사용법

### 대용량 데이터 처리

```python
# Dask 청킹 활용
ds = cu.load_dataset('huge_file.nc', 
                     chunks={'time': 365, 'latitude': 50, 'longitude': 50})

# 지연 계산 활용
lazy_mean = cu.calculate_spatial_mean(ds, 'sst')
result = lazy_mean.compute()  # 실제 계산 실행
```

### 배치 처리

```python
import glob

# 여러 파일 처리
nc_files = glob.glob('data/*.nc')
results = []

for file in nc_files:
    ds = cu.load_dataset(file)
    ts = cu.create_timeseries(ds, 'sst', spatial_mean=True)
    trend = cu.calculate_trend(ts)
    results.append({
        'file': file,
        'trend': trend['slope'],
        'r_squared': trend['r_squared']
    })

# 결과 저장
import pandas as pd
results_df = pd.DataFrame(results)
results_df.to_csv('batch_results.csv')
```

### 데이터셋 병합

```python
# 여러 데이터셋 병합
datasets = [ds1, ds2, ds3]
merged = cu.merge_datasets(datasets, dim='time')

# 다른 차원으로 병합
merged_spatial = cu.merge_datasets(datasets, dim='longitude', method='outer')
```

### 품질 관리

```python
# 데이터 품질 검사
qc = cu.quality_check(ds, 'sst', 
                      valid_range=(-2, 35),
                      min_coverage=0.8,
                      max_gap=30)

if qc['quality_pass']:
    print("품질 검사 통과")
else:
    print(f"문제: 커버리지 {qc['coverage']:.1%}")
```

### 필터링

```python
# 저주파 필터 (장기 변동 추출)
filtered = cu.apply_filter(ts, filter_type='lowpass', 
                          cutoff_freq=0.1, order=5)

# 고주파 필터 (단기 변동 추출)
filtered = cu.apply_filter(ts, filter_type='highpass', 
                          cutoff_freq=0.5, order=3)

# 밴드패스 필터
filtered = cu.apply_filter(ts, filter_type='bandpass', 
                          cutoff_freq=[0.1, 0.5], order=4)
```

### 이동평균

```python
# 중앙 정렬 이동평균
smoothed = cu.apply_moving_average(ts, window=30, center=True)

# 후진 이동평균
smoothed = cu.apply_moving_average(ts, window=30, center=False)

# 최소 데이터 요구사항
smoothed = cu.apply_moving_average(ts, window=30, min_periods=15)
```

## 문제 해결

### 일반적인 오류

#### 1. 메모리 부족 오류
```python
# 해결책: 청킹 사용
ds = cu.load_dataset('large_file.nc', 
                     chunks={'time': 100, 'lat': 20, 'lon': 20})
```

#### 2. 차원 이름 오류
```python
# 해결책: 차원 이름 명시
ds_subset = cu.subset_region(ds, (120, 130), (30, 40),
                            lon_dim='x', lat_dim='y')
```

#### 3. 시간 형식 오류
```python
# 해결책: 시간 디코딩 비활성화 후 수동 처리
ds = cu.load_dataset('data.nc', decode_times=False)
ds['time'] = pd.to_datetime(ds.time, unit='days', origin='1900-01-01')
```

#### 4. 시각화 오류 (헤드리스 환경)
```python
import matplotlib
matplotlib.use('Agg')  # 백엔드 설정
import matplotlib.pyplot as plt
```

### 성능 이슈

#### 느린 계산 속도
```python
# Dask 병렬 처리 활용
import dask
dask.config.set(scheduler='threads', num_workers=4)

# 청킹 크기 조정
ds = ds.chunk({'time': 500, 'lat': 100, 'lon': 100})
```

#### 높은 메모리 사용량
```python
# 지연 계산 활용
result = ds.mean('time')  # 지연 계산
final = result.compute()  # 필요할 때만 계산

# 중간 결과 삭제
del intermediate_result
import gc
gc.collect()
```

## 최적화 팁

### 1. 데이터 전처리 최적화

```python
# 필요한 영역만 먼저 추출
ds = cu.load_dataset('global_data.nc')
ds_region = cu.subset_region(ds, region_bounds)  # 먼저 지역 추출
ds_time = cu.subset_time(ds_region, time_range)  # 그 다음 시간 추출
```

### 2. 효율적인 청킹

```python
# 시간 축 분석이 많은 경우
ds = ds.chunk({'time': -1, 'lat': 50, 'lon': 50})

# 공간 분석이 많은 경우
ds = ds.chunk({'time': 100, 'lat': -1, 'lon': -1})
```

### 3. 계산 순서 최적화

```python
# 비효율적
ts = cu.create_timeseries(ds, 'sst', spatial_mean=True)
trend = cu.calculate_trend(ts)

# 효율적: 지역 추출 먼저
ds_small = cu.subset_region(ds, region_bounds)
ts = cu.create_timeseries(ds_small, 'sst', spatial_mean=True)
trend = cu.calculate_trend(ts)
```

### 4. 메모리 사용량 모니터링

```python
import psutil
import os

def check_memory():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"메모리 사용량: {memory_mb:.1f} MB")

check_memory()
# 분석 수행
check_memory()
```

### 5. 캐싱 활용

```python
# 중간 결과 저장
processed_ds = cu.subset_region(ds, region_bounds)
processed_ds.to_netcdf('processed_data.nc')

# 재사용
processed_ds = cu.load_dataset('processed_data.nc')
```

## 예제 스크립트 모음

### 배치 분석 스크립트

```python
#!/usr/bin/env python3
"""
배치 분석 스크립트 예제
여러 지역의 SST 트렌드를 일괄 분석
"""

import copernicus_utils as cu
import pandas as pd
import sys

# 분석할 지역들
regions = {
    'East_Sea': {'lon': (128, 142), 'lat': (35, 45)},
    'Yellow_Sea': {'lon': (119, 126), 'lat': (33, 38)},
    'South_Sea': {'lon': (126, 130), 'lat': (32, 35)}
}

# 데이터 로딩
try:
    ds = cu.load_dataset(sys.argv[1])
    print(f"데이터 로딩 완료: {sys.argv[1]}")
except:
    print("사용법: python batch_analysis.py data.nc")
    sys.exit(1)

# 각 지역 분석
results = []
for region_name, coords in regions.items():
    print(f"\n{region_name} 분석 중...")
    
    # 지역 추출
    ds_region = cu.subset_region(ds, coords['lon'], coords['lat'])
    
    # 시계열 생성
    ts = cu.create_timeseries(ds_region, 'sst', spatial_mean=True)
    
    # 트렌드 분석
    trend = cu.calculate_trend(ts)
    
    # 극값 분석
    extremes = cu.detect_extremes(ts, threshold_type='percentile', 
                                 threshold_value=95)
    
    # 결과 저장
    results.append({
        'region': region_name,
        'trend_per_year': trend['slope'] * 365.25,
        'r_squared': trend['r_squared'],
        'p_value': trend['p_value'],
        'num_extremes': len(extremes),
        'mean_temp': float(ts.mean()),
        'std_temp': float(ts.std())
    })

# 결과 출력 및 저장
results_df = pd.DataFrame(results)
print("\n=== 분석 결과 ===")
print(results_df.round(3))

results_df.to_csv('regional_analysis_results.csv', index=False)
print("\n결과가 'regional_analysis_results.csv'에 저장되었습니다.")
```

### 품질 검사 스크립트

```python
#!/usr/bin/env python3
"""
데이터 품질 일괄 검사 스크립트
"""

import copernicus_utils as cu
import glob
import pandas as pd

# 모든 NetCDF 파일 찾기
nc_files = glob.glob('data/*.nc')

quality_results = []

for file_path in nc_files:
    print(f"검사 중: {file_path}")
    
    try:
        # 데이터 로딩
        ds = cu.load_dataset(file_path)
        
        # 각 변수 품질 검사
        for var_name in ds.data_vars:
            qc = cu.quality_check(ds, var_name, min_coverage=0.8)
            
            quality_results.append({
                'file': file_path,
                'variable': var_name,
                'coverage': qc['coverage'],
                'missing_percent': qc['missing_percent'],
                'quality_pass': qc['quality_pass'],
                'mean': qc['mean'],
                'std': qc['std']
            })
            
    except Exception as e:
        print(f"오류 발생 ({file_path}): {e}")

# 결과 저장
if quality_results:
    qc_df = pd.DataFrame(quality_results)
    qc_df.to_csv('quality_check_results.csv', index=False)
    
    # 품질 요약
    print("\n=== 품질 검사 요약 ===")
    print(f"전체 검사 항목: {len(qc_df)}")
    print(f"품질 통과: {qc_df['quality_pass'].sum()}")
    print(f"품질 실패: {(~qc_df['quality_pass']).sum()}")
    print(f"평균 커버리지: {qc_df['coverage'].mean():.1%}")
```

이 가이드를 통해 코페르니쿠스 해양 연구 분석 시스템을 효과적으로 활용하실 수 있습니다. 추가 질문이나 도움이 필요하시면 GitHub Issues를 통해 문의해 주세요.