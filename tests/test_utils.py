#!/usr/bin/env python3
"""
Copernicus Utils 테스트 스위트
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import xarray as xr
from datetime import datetime, timedelta

# 상위 디렉토리의 모듈 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import copernicus_utils as cu


class TestCopernicusUtils(unittest.TestCase):
    """Copernicus Utils 테스트 클래스"""
    
    def setUp(self):
        """테스트용 샘플 데이터 생성"""
        # 시간, 위도, 경도 좌표
        self.time = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        self.lat = np.arange(30, 40, 0.5)
        self.lon = np.arange(120, 130, 0.5)
        
        # 샘플 SST 데이터 생성
        np.random.seed(42)
        sst_data = np.random.randn(len(self.time), len(self.lat), len(self.lon)) * 2 + 15
        
        # 계절 변동 추가
        for t, date in enumerate(self.time):
            seasonal = 10 * np.sin(2 * np.pi * date.dayofyear / 365.25)
            sst_data[t, :, :] += seasonal
        
        # xarray Dataset 생성
        self.ds = xr.Dataset(
            {
                'sst': (['time', 'latitude', 'longitude'], sst_data),
                'salinity': (['time', 'latitude', 'longitude'], 
                            35 + np.random.randn(*sst_data.shape) * 0.5)
            },
            coords={
                'time': self.time,
                'latitude': self.lat,
                'longitude': self.lon
            }
        )
        
        # 속성 설정
        self.ds['sst'].attrs = {
            'units': '°C',
            'long_name': 'Sea Surface Temperature',
            'valid_min': -2.0,
            'valid_max': 35.0
        }
        
    def test_subset_region(self):
        """지역 추출 함수 테스트"""
        lon_range = (122, 128)
        lat_range = (32, 38)
        
        subset = cu.subset_region(self.ds, lon_range, lat_range)
        
        # 추출된 지역이 올바른지 확인
        self.assertLessEqual(subset.longitude.min(), lon_range[0])
        self.assertGreaterEqual(subset.longitude.max(), lon_range[1])
        self.assertLessEqual(subset.latitude.min(), lat_range[0])
        self.assertGreaterEqual(subset.latitude.max(), lat_range[1])
        
        # 데이터 크기 확인
        self.assertLess(len(subset.longitude), len(self.ds.longitude))
        self.assertLess(len(subset.latitude), len(self.ds.latitude))
        
    def test_subset_time(self):
        """시간 추출 함수 테스트"""
        start_date = '2020-06-01'
        end_date = '2020-08-31'
        
        subset = cu.subset_time(self.ds, start_date, end_date)
        
        # 시간 범위 확인
        self.assertGreaterEqual(subset.time.min().values, pd.to_datetime(start_date).values)
        self.assertLessEqual(subset.time.max().values, pd.to_datetime(end_date).values)
        
        # 데이터 크기 확인
        self.assertLess(len(subset.time), len(self.ds.time))
        
    def test_calculate_spatial_mean(self):
        """공간 평균 계산 함수 테스트"""
        # 위도 가중치 적용
        mean_weighted = cu.calculate_spatial_mean(self.ds, 'sst', weighted=True)
        
        # 단순 평균
        mean_simple = cu.calculate_spatial_mean(self.ds, 'sst', weighted=False)
        
        # 시계열 길이 확인
        self.assertEqual(len(mean_weighted), len(self.time))
        self.assertEqual(len(mean_simple), len(self.time))
        
        # 값이 합리적인 범위인지 확인
        self.assertTrue(mean_weighted.min() > 0)
        self.assertTrue(mean_weighted.max() < 30)
        
    def test_create_timeseries(self):
        """시계열 생성 함수 테스트"""
        # 공간 평균 시계열
        ts_mean = cu.create_timeseries(self.ds, 'sst', spatial_mean=True)
        
        # 특정 지점 시계열
        ts_point = cu.create_timeseries(self.ds, 'sst', 
                                       lon_point=125, lat_point=35)
        
        # pandas Series 확인
        self.assertIsInstance(ts_mean, pd.Series)
        self.assertIsInstance(ts_point, pd.Series)
        
        # 길이 확인
        self.assertEqual(len(ts_mean), len(self.time))
        self.assertEqual(len(ts_point), len(self.time))
        
    def test_calculate_anomaly(self):
        """이상치 계산 함수 테스트"""
        anomaly = cu.calculate_anomaly(self.ds, 'sst')
        
        # 차원 확인
        self.assertEqual(anomaly.dims, self.ds['sst'].dims)
        self.assertEqual(anomaly.shape, self.ds['sst'].shape)
        
        # 이상치의 평균이 대략 0에 가까운지 확인
        self.assertAlmostEqual(float(anomaly.mean()), 0, delta=0.1)
        
    def test_apply_moving_average(self):
        """이동평균 함수 테스트"""
        # 시계열 생성
        ts = cu.create_timeseries(self.ds, 'sst', spatial_mean=True)
        
        # 30일 이동평균
        ts_smooth = cu.apply_moving_average(ts, window=30, center=True)
        
        # 길이 확인
        self.assertEqual(len(ts_smooth), len(ts))
        
        # 스무딩 효과 확인 (분산이 줄어들어야 함)
        self.assertLess(ts_smooth.std(), ts.std())
        
    def test_calculate_trend(self):
        """트렌드 계산 함수 테스트"""
        # 트렌드가 있는 시계열 생성
        ts = pd.Series(
            np.arange(100) * 0.1 + np.random.randn(100) * 0.5,
            index=pd.date_range('2020-01-01', periods=100, freq='D')
        )
        
        # 선형 트렌드 계산
        trend = cu.calculate_trend(ts, method='linear')
        
        # 결과 구조 확인
        required_keys = ['slope', 'intercept', 'r_squared', 'p_value', 'trend_line']
        for key in required_keys:
            self.assertIn(key, trend)
        
        # 트렌드가 양수인지 확인 (상승 트렌드)
        self.assertGreater(trend['slope'], 0)
        
    def test_calculate_correlation(self):
        """상관관계 계산 함수 테스트"""
        # 두 시계열 생성 (서로 상관관계가 있도록)
        x = np.random.randn(100)
        y = x * 0.8 + np.random.randn(100) * 0.2  # 강한 양의 상관관계
        
        ts1 = pd.Series(x)
        ts2 = pd.Series(y)
        
        # 상관관계 계산
        corr, pval = cu.calculate_correlation(ts1, ts2)
        
        # 강한 양의 상관관계 확인
        self.assertGreater(corr, 0.7)
        self.assertLess(pval, 0.05)  # 유의미한 상관관계
        
    def test_detect_extremes(self):
        """극값 탐지 함수 테스트"""
        # 극값이 포함된 시계열 생성
        data = np.random.randn(1000)
        data[100:110] = 3  # 극값 이벤트
        data[500:505] = 3.5  # 또 다른 극값 이벤트
        
        ts = pd.Series(data, index=pd.date_range('2020-01-01', periods=1000, freq='D'))
        
        # 95 퍼센타일 극값 탐지
        extremes = cu.detect_extremes(ts, threshold_type='percentile', threshold_value=95)
        
        # 이벤트가 탐지되었는지 확인
        self.assertGreater(len(extremes), 0)
        
        # DataFrame 구조 확인
        expected_columns = ['start', 'end', 'duration', 'max_value', 'mean_value', 'sum_excess']
        for col in expected_columns:
            self.assertIn(col, extremes.columns)
            
    def test_quality_check(self):
        """데이터 품질 검사 함수 테스트"""
        qc = cu.quality_check(self.ds, 'sst', valid_range=(-2, 35), min_coverage=0.8)
        
        # 결과 구조 확인
        required_keys = ['variable', 'total_points', 'missing_count', 'coverage', 'quality_pass']
        for key in required_keys:
            self.assertIn(key, qc)
        
        # 품질 검사 통과 확인 (완전한 데이터이므로)
        self.assertTrue(qc['quality_pass'])
        self.assertGreaterEqual(qc['coverage'], 0.99)
        
    def test_export_to_csv(self):
        """CSV 내보내기 함수 테스트"""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # 시계열 데이터 CSV 저장
            ts = cu.create_timeseries(self.ds, 'sst', spatial_mean=True)
            cu.export_to_csv(ts, tmp_path)
            
            # 파일이 생성되었는지 확인
            self.assertTrue(os.path.exists(tmp_path))
            
            # 파일 내용 확인
            df_read = pd.read_csv(tmp_path, index_col=0)
            self.assertEqual(len(df_read), len(ts))
            
        finally:
            # 임시 파일 삭제
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    def test_list_variables(self):
        """변수 목록 함수 테스트"""
        var_info = cu.list_variables(self.ds)
        
        # DataFrame 반환 확인
        self.assertIsInstance(var_info, pd.DataFrame)
        
        # 변수가 모두 포함되었는지 확인
        expected_vars = ['sst', 'salinity']
        for var in expected_vars:
            self.assertIn(var, var_info['variable'].values)
        
        # 필요한 컬럼 확인
        expected_columns = ['variable', 'dimensions', 'shape', 'dtype']
        for col in expected_columns:
            self.assertIn(col, var_info.columns)


class TestScrapingFunctions(unittest.TestCase):
    """스크래핑 관련 함수 테스트"""
    
    def setUp(self):
        """테스트용 스크래퍼 설정"""
        # 실제 네트워크 요청을 하지 않도록 mock 사용
        self.test_html = '''
        <html>
            <body>
                <a href="/tutorial1.ipynb">Tutorial 1</a>
                <a href="/tutorial2.ipynb">Tutorial 2</a>
                <a href="/data.nc">Sample Data</a>
            </body>
        </html>
        '''
        
    @patch('requests.Session.get')
    def test_scraper_initialization(self, mock_get):
        """스크래퍼 초기화 테스트"""
        from scrape_copernicus import CopernicusScraper
        
        # Mock response 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = self.test_html
        mock_get.return_value = mock_response
        
        # 스크래퍼 생성
        scraper = CopernicusScraper()
        self.assertIsNotNone(scraper)
        self.assertEqual(scraper.base_url, 
                        "https://marine.copernicus.eu/services/user-learning-services/tutorials")
        
    def test_sanitize_filename(self):
        """파일명 정제 함수 테스트"""
        from scrape_copernicus import CopernicusScraper
        
        scraper = CopernicusScraper()
        
        # 특수문자 제거 테스트
        result = scraper.sanitize_filename("Tutorial: SST Analysis (v1.0)")
        expected = "Tutorial_SST_Analysis_v1_0"
        self.assertEqual(result, expected)
        
        # 긴 파일명 제한 테스트
        long_name = "A" * 100
        result = scraper.sanitize_filename(long_name)
        self.assertLessEqual(len(result), 50)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_full_analysis_pipeline(self):
        """전체 분석 파이프라인 테스트"""
        # 샘플 데이터 생성
        time = pd.date_range('2020-01-01', '2020-12-31', freq='D')
        lat = np.arange(30, 35, 1.0)
        lon = np.arange(120, 125, 1.0)
        
        sst_data = 15 + 10 * np.sin(2 * np.pi * np.arange(len(time)) / 365.25) + \
                   np.random.randn(len(time), len(lat), len(lon)) * 2
        
        ds = xr.Dataset(
            {'sst': (['time', 'latitude', 'longitude'], sst_data)},
            coords={'time': time, 'latitude': lat, 'longitude': lon}
        )
        
        # 전체 분석 파이프라인 실행
        # 1. 지역 추출
        ds_region = cu.subset_region(ds, (121, 124), (31, 34))
        
        # 2. 시간 추출
        ds_subset = cu.subset_time(ds_region, '2020-06-01', '2020-08-31')
        
        # 3. 시계열 생성
        ts = cu.create_timeseries(ds_subset, 'sst', spatial_mean=True)
        
        # 4. 트렌드 분석
        trend = cu.calculate_trend(ts, method='linear')
        
        # 5. 이상치 계산
        anomaly = cu.calculate_anomaly(ds_subset, 'sst')
        
        # 결과 검증
        self.assertIsInstance(ts, pd.Series)
        self.assertIn('slope', trend)
        self.assertEqual(anomaly.dims, ds_subset['sst'].dims)
        
        # 파이프라인이 오류 없이 실행되었음을 확인
        self.assertTrue(True)


def run_performance_tests():
    """성능 테스트 실행"""
    import time
    
    print("성능 테스트 실행 중...")
    
    # 대용량 데이터 생성
    time_coords = pd.date_range('2000-01-01', '2023-12-31', freq='D')
    lat_coords = np.arange(20, 50, 0.25)  # 0.25도 해상도
    lon_coords = np.arange(110, 150, 0.25)
    
    print(f"테스트 데이터 크기: {len(time_coords)} × {len(lat_coords)} × {len(lon_coords)}")
    
    # 메모리 효율적인 데이터 생성 (청킹 사용)
    chunks = {'time': 365, 'latitude': 50, 'longitude': 50}
    
    # 간단한 패턴으로 데이터 생성 (메모리 절약)
    sst_data = np.random.randn(len(time_coords), len(lat_coords), len(lon_coords)) * 2 + 15
    
    ds_large = xr.Dataset(
        {'sst': (['time', 'latitude', 'longitude'], sst_data)},
        coords={
            'time': time_coords,
            'latitude': lat_coords, 
            'longitude': lon_coords
        }
    )
    
    # 청킹 적용
    ds_large = ds_large.chunk(chunks)
    
    # 성능 테스트 함수들
    performance_tests = [
        ('지역 추출', lambda: cu.subset_region(ds_large, (125, 135), (35, 45))),
        ('공간 평균', lambda: cu.calculate_spatial_mean(ds_large.isel(time=slice(0, 365)), 'sst')),
        ('시계열 생성', lambda: cu.create_timeseries(ds_large.isel(time=slice(0, 365)), 'sst', spatial_mean=True))
    ]
    
    results = {}
    for test_name, test_func in performance_tests:
        start_time = time.time()
        try:
            result = test_func()
            end_time = time.time()
            elapsed = end_time - start_time
            results[test_name] = elapsed
            print(f"  {test_name}: {elapsed:.2f}초")
        except Exception as e:
            print(f"  {test_name}: 실패 ({str(e)})")
            results[test_name] = None
    
    return results


if __name__ == '__main__':
    # 단위 테스트 실행
    print("=" * 50)
    print("Copernicus Utils 테스트 시작")
    print("=" * 50)
    
    # 테스트 스위트 생성
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 테스트 클래스 추가
    test_classes = [TestCopernicusUtils, TestScrapingFunctions, TestIntegration]
    
    for test_class in test_classes:
        tests = test_loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 테스트 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    print(f"실행된 테스트: {result.testsRun}")
    print(f"실패: {len(result.failures)}")
    print(f"에러: {len(result.errors)}")
    
    if result.failures:
        print("\n실패한 테스트:")
        for test, failure in result.failures:
            print(f"  - {test}: {failure}")
    
    if result.errors:
        print("\n에러가 발생한 테스트:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")
    
    # 성능 테스트 (선택적)
    run_performance = input("\n성능 테스트를 실행하시겠습니까? (y/n): ").lower().startswith('y')
    if run_performance:
        print("\n" + "=" * 50)
        print("성능 테스트")
        print("=" * 50)
        performance_results = run_performance_tests()
    
    # 전체 결과
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n전체 테스트 결과: {'✓ 통과' if success else '✗ 실패'}")
    
    sys.exit(0 if success else 1)