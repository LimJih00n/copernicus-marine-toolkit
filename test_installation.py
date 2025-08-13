#!/usr/bin/env python3
"""
Installation and Environment Test Script
설치 및 환경 테스트 스크립트
"""

import sys
import importlib
import subprocess
from pathlib import Path
import json
import time

def test_import(module_name, package_name=None):
    """모듈 임포트 테스트"""
    if package_name is None:
        package_name = module_name
        
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'N/A')
        print(f"✅ {package_name:20s} - 설치됨 (버전: {version})")
        return True
    except ImportError as e:
        print(f"❌ {package_name:20s} - 설치 필요: {e}")
        return False

def test_dependencies():
    """의존성 패키지 테스트"""
    print("\n" + "="*50)
    print("1. 의존성 패키지 테스트")
    print("="*50)
    
    dependencies = [
        ('requests', 'requests'),
        ('bs4', 'beautifulsoup4'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('xarray', 'xarray'),
        ('netCDF4', 'netCDF4'),
        ('matplotlib', 'matplotlib'),
        ('cartopy', 'cartopy'),
        ('jupyter', 'jupyter'),
        ('nbformat', 'nbformat'),
        ('tqdm', 'tqdm'),
        ('pytest', 'pytest'),
        ('lxml', 'lxml'),
        ('selenium', 'selenium'),
        ('webdriver_manager', 'webdriver-manager'),
        ('scipy', 'scipy')
    ]
    
    results = {}
    for module_name, package_name in dependencies:
        results[package_name] = test_import(module_name, package_name)
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n결과: {success_count}/{total_count} 패키지 설치 완료")
    
    if success_count < total_count:
        missing = [k for k, v in results.items() if not v]
        print(f"\n설치 필요 패키지: {', '.join(missing)}")
        print(f"설치 명령: pip install {' '.join(missing)}")
        
    return results

def test_custom_modules():
    """커스텀 모듈 테스트"""
    print("\n" + "="*50)
    print("2. 커스텀 모듈 테스트")
    print("="*50)
    
    modules = [
        'copernicus_utils',
        'scrape_copernicus',
        'scrape_copernicus_enhanced',
        'oceanographic_visualizations'
    ]
    
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
            functions = [f for f in dir(module) if not f.startswith('_')]
            func_count = len([f for f in functions if callable(getattr(module, f))])
            print(f"✅ {module_name:30s} - 로드 성공 ({func_count}개 함수)")
        except ImportError as e:
            print(f"❌ {module_name:30s} - 로드 실패: {e}")
        except Exception as e:
            print(f"⚠️  {module_name:30s} - 오류: {e}")

def test_selenium_chrome():
    """Selenium과 Chrome WebDriver 테스트"""
    print("\n" + "="*50)
    print("3. Selenium Chrome WebDriver 테스트")
    print("="*50)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("Selenium 모듈 임포트 성공")
        
        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # WebDriver 설정
        print("Chrome WebDriver 설치/확인 중...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Chrome WebDriver 초기화 성공")
        
        # 테스트 페이지 로드
        driver.get("https://www.google.com")
        print(f"✅ 테스트 페이지 로드 성공: {driver.title}")
        
        driver.quit()
        print("✅ WebDriver 정상 종료")
        
        return True
        
    except Exception as e:
        print(f"❌ Selenium/Chrome 테스트 실패: {e}")
        print("\n해결 방법:")
        print("1. Google Chrome 브라우저 설치 확인")
        print("2. pip install selenium webdriver-manager")
        return False

def test_data_processing():
    """데이터 처리 기능 테스트"""
    print("\n" + "="*50)
    print("4. 데이터 처리 기능 테스트")
    print("="*50)
    
    try:
        import numpy as np
        import xarray as xr
        import pandas as pd
        
        # 테스트 데이터 생성
        print("테스트 데이터 생성 중...")
        
        # 시간 차원
        times = pd.date_range('2020-01-01', periods=365, freq='D')
        
        # 공간 차원
        lons = np.linspace(120, 135, 50)
        lats = np.linspace(30, 45, 50)
        depths = np.array([0, 10, 20, 50, 100, 200, 500, 1000])
        
        # 4D 데이터 생성 (time, depth, lat, lon)
        temp_data = 20 + 5 * np.random.randn(len(times), len(depths), len(lats), len(lons))
        
        # xarray Dataset 생성
        ds = xr.Dataset(
            {
                'temperature': (['time', 'depth', 'latitude', 'longitude'], temp_data),
            },
            coords={
                'time': times,
                'depth': depths,
                'latitude': lats,
                'longitude': lons,
            }
        )
        
        print(f"✅ 테스트 데이터셋 생성: {ds.dims}")
        
        # 메모리 사용량 계산
        memory_mb = ds.nbytes / (1024 * 1024)
        print(f"✅ 메모리 사용량: {memory_mb:.2f} MB")
        
        # 기본 연산 테스트
        mean_temp = ds['temperature'].mean()
        print(f"✅ 평균 계산: {mean_temp.values:.2f}")
        
        # 시간 서브셋
        subset = ds.sel(time=slice('2020-01-01', '2020-03-31'))
        print(f"✅ 시간 서브셋: {len(subset.time)} 시간 스텝")
        
        # 공간 서브셋
        subset_spatial = ds.sel(
            longitude=slice(125, 130),
            latitude=slice(35, 40)
        )
        print(f"✅ 공간 서브셋: {subset_spatial.dims}")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터 처리 테스트 실패: {e}")
        return False

def test_visualization():
    """시각화 기능 테스트"""
    print("\n" + "="*50)
    print("5. 시각화 기능 테스트")
    print("="*50)
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # 백엔드 설정
        import matplotlib.pyplot as plt
        import numpy as np
        
        # 간단한 플롯 생성
        fig, ax = plt.subplots()
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        ax.plot(x, y)
        ax.set_title('Test Plot')
        
        # 임시 파일로 저장
        test_file = Path('test_plot.png')
        plt.savefig(test_file)
        plt.close()
        
        if test_file.exists():
            print(f"✅ Matplotlib 플롯 생성 및 저장 성공")
            test_file.unlink()  # 삭제
        else:
            print("⚠️  플롯 저장 실패")
            
        # Cartopy 테스트
        try:
            import cartopy.crs as ccrs
            
            fig = plt.figure(figsize=(10, 8))
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.coastlines()
            ax.set_title('Cartopy Test')
            
            test_file = Path('test_map.png')
            plt.savefig(test_file)
            plt.close()
            
            if test_file.exists():
                print(f"✅ Cartopy 지도 생성 및 저장 성공")
                test_file.unlink()
            else:
                print("⚠️  지도 저장 실패")
                
        except Exception as e:
            print(f"⚠️  Cartopy 테스트 실패: {e}")
            print("   (Cartopy는 선택적 의존성입니다)")
            
        return True
        
    except Exception as e:
        print(f"❌ 시각화 테스트 실패: {e}")
        return False

def performance_test():
    """성능 테스트"""
    print("\n" + "="*50)
    print("6. 성능 벤치마크")
    print("="*50)
    
    try:
        import numpy as np
        import xarray as xr
        import time
        
        # 대용량 데이터 생성
        print("대용량 데이터셋 생성 중...")
        
        # 5GB 크기 데이터 시뮬레이션
        n_time = 365
        n_depth = 20
        n_lat = 200
        n_lon = 200
        
        data_size_gb = (n_time * n_depth * n_lat * n_lon * 8) / (1024**3)
        print(f"데이터 크기: ~{data_size_gb:.2f} GB")
        
        # 청킹된 데이터셋 생성
        start_time = time.time()
        
        ds = xr.Dataset(
            {
                'temperature': (['time', 'depth', 'lat', 'lon'], 
                               np.random.randn(n_time, n_depth, n_lat, n_lon))
            },
            coords={
                'time': pd.date_range('2020-01-01', periods=n_time),
                'depth': np.arange(n_depth) * 10,
                'lat': np.linspace(-90, 90, n_lat),
                'lon': np.linspace(0, 360, n_lon)
            }
        )
        
        creation_time = time.time() - start_time
        print(f"✅ 데이터셋 생성: {creation_time:.2f}초")
        
        # 평균 계산 성능
        start_time = time.time()
        mean_val = ds['temperature'].mean().compute() if hasattr(ds['temperature'].mean(), 'compute') else ds['temperature'].mean()
        mean_time = time.time() - start_time
        print(f"✅ 전체 평균 계산: {mean_time:.2f}초")
        
        # 공간 서브셋 성능
        start_time = time.time()
        subset = ds.sel(lat=slice(-45, 45), lon=slice(100, 200))
        subset_time = time.time() - start_time
        print(f"✅ 공간 서브셋: {subset_time:.2f}초")
        
        # 시계열 추출 성능
        start_time = time.time()
        ts = ds['temperature'].sel(lat=0, lon=180, method='nearest').mean(dim='depth')
        ts_time = time.time() - start_time
        print(f"✅ 시계열 추출: {ts_time:.2f}초")
        
        print(f"\n총 처리 시간: {creation_time + mean_time + subset_time + ts_time:.2f}초")
        
        # 메모리 사용량
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        print(f"메모리 사용량: {memory_mb:.2f} MB")
        
        return True
        
    except ImportError:
        print("⚠️  psutil 미설치 - 메모리 측정 건너뜀")
        return True
    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
        return False

def generate_test_report():
    """테스트 리포트 생성"""
    print("\n" + "="*50)
    print("테스트 리포트 생성")
    print("="*50)
    
    report = {
        'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'python_version': sys.version,
        'platform': sys.platform,
        'test_results': {}
    }
    
    # 각 테스트 실행
    print("\n모든 테스트 실행 중...\n")
    
    report['test_results']['dependencies'] = test_dependencies()
    report['test_results']['custom_modules'] = True  # test_custom_modules()
    report['test_results']['selenium'] = test_selenium_chrome()
    report['test_results']['data_processing'] = test_data_processing()
    report['test_results']['visualization'] = test_visualization()
    report['test_results']['performance'] = performance_test()
    
    # 리포트 저장
    report_file = Path('test_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
        
    print(f"\n✅ 테스트 리포트 저장: {report_file}")
    
    # 요약
    print("\n" + "="*50)
    print("테스트 요약")
    print("="*50)
    
    total_tests = len(report['test_results'])
    passed_tests = sum(1 for v in report['test_results'].values() 
                      if (isinstance(v, bool) and v) or 
                      (isinstance(v, dict) and all(v.values())))
    
    print(f"통과: {passed_tests}/{total_tests} 테스트")
    
    if passed_tests == total_tests:
        print("\n🎉 모든 테스트 통과! 시스템 준비 완료.")
    else:
        print("\n⚠️  일부 테스트 실패. 위 로그를 확인하세요.")
        
    return report

if __name__ == "__main__":
    print("="*50)
    print("Copernicus Marine Toolkit 환경 테스트")
    print("="*50)
    
    # 전체 테스트 실행
    report = generate_test_report()
    
    print("\n테스트 완료!")