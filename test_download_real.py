#!/usr/bin/env python3
"""
실제 다운로드 테스트 - Copernicus Marine Service
실제 파일 다운로드 및 검증
"""

import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time
import hashlib

def test_real_downloads():
    """실제 파일 다운로드 테스트"""
    
    print("="*50)
    print("실제 파일 다운로드 테스트")
    print("="*50)
    
    # 세션 설정
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # 다운로드 디렉토리
    download_dir = Path('test_real_downloads')
    download_dir.mkdir(exist_ok=True)
    
    # 1. 먼저 튜토리얼 페이지에서 실제 다운로드 링크 찾기
    print("\n1. 튜토리얼 페이지 스캔...")
    base_url = "https://marine.copernicus.eu"
    tutorial_urls = [
        "/services/user-learning-services/tutorials",
        "/services/user-learning-services/arctic-ocean-training-2022-how-process-reanalysis-copernicus-marine",
        "/services/user-learning-services"
    ]
    
    download_links = []
    
    for path in tutorial_urls:
        url = base_url + path
        print(f"\n스캔: {url}")
        
        try:
            response = session.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 다운로드 가능한 링크 패턴들
                # .zip, .pdf, .ipynb, .nc, download 링크 등
                patterns = [
                    soup.find_all('a', href=lambda x: x and '.zip' in x.lower()),
                    soup.find_all('a', href=lambda x: x and '.pdf' in x.lower()),
                    soup.find_all('a', href=lambda x: x and '.ipynb' in x.lower()),
                    soup.find_all('a', href=lambda x: x and 'download' in x.lower()),
                    soup.find_all('a', {'download': True}),  # download 속성이 있는 링크
                ]
                
                for links in patterns:
                    for link in links[:2]:  # 각 패턴당 최대 2개
                        href = link.get('href', '')
                        if href:
                            # 절대 URL로 변환
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    href = base_url + href
                                else:
                                    href = url + '/' + href
                            
                            # 중복 제거
                            if href not in [d['url'] for d in download_links]:
                                download_links.append({
                                    'url': href,
                                    'text': link.get_text(strip=True)[:50],
                                    'source_page': url
                                })
                
                print(f"  → {len(download_links)} 다운로드 링크 발견")
                
        except Exception as e:
            print(f"  ❌ 에러: {str(e)}")
    
    print(f"\n총 {len(download_links)}개 다운로드 링크 발견")
    
    # 2. 발견된 링크 다운로드 시도
    print("\n2. 다운로드 시도...")
    print("-" * 40)
    
    success_count = 0
    failed_count = 0
    results = []
    
    for i, link_info in enumerate(download_links[:5], 1):  # 최대 5개만 테스트
        print(f"\n[{i}/{min(5, len(download_links))}] 다운로드 시도")
        print(f"  URL: {link_info['url'][:80]}...")
        print(f"  설명: {link_info['text']}")
        
        try:
            # HEAD 요청으로 먼저 확인
            head_response = session.head(link_info['url'], allow_redirects=True, timeout=10)
            content_type = head_response.headers.get('content-type', '')
            content_length = head_response.headers.get('content-length', '0')
            
            print(f"  타입: {content_type}")
            if content_length != '0':
                size_mb = int(content_length) / (1024 * 1024)
                print(f"  크기: {size_mb:.2f} MB")
            
            # 실제 다운로드 (최대 10MB만)
            if int(content_length) < 10 * 1024 * 1024 or content_length == '0':
                response = session.get(link_info['url'], stream=True, timeout=30)
                response.raise_for_status()
                
                # 파일명 결정
                if 'content-disposition' in response.headers:
                    import re
                    d = response.headers['content-disposition']
                    fname = re.findall('filename="?(.+)"?', d)
                    if fname:
                        filename = fname[0].strip('"')
                    else:
                        filename = link_info['url'].split('/')[-1].split('?')[0] or 'download'
                else:
                    filename = link_info['url'].split('/')[-1].split('?')[0] or 'download'
                
                # 확장자가 없으면 content-type 기반으로 추가
                if '.' not in filename:
                    if 'pdf' in content_type:
                        filename += '.pdf'
                    elif 'zip' in content_type:
                        filename += '.zip'
                    elif 'html' in content_type:
                        filename += '.html'
                    else:
                        filename += '.bin'
                
                filepath = download_dir / f"{i:02d}_{filename[:50]}"
                
                # 다운로드
                downloaded_size = 0
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if downloaded_size > 10 * 1024 * 1024:  # 10MB 제한
                                break
                
                # 파일 검증
                actual_size = filepath.stat().st_size
                print(f"  ✅ 다운로드 완료: {filepath.name}")
                print(f"     크기: {actual_size / 1024:.2f} KB")
                
                # 파일 타입 확인
                with open(filepath, 'rb') as f:
                    header = f.read(16)
                    if header.startswith(b'PK'):
                        print(f"     타입: ZIP 파일")
                    elif header.startswith(b'%PDF'):
                        print(f"     타입: PDF 파일")
                    elif b'<html' in header or b'<!DOCTYPE' in header:
                        print(f"     타입: HTML 파일")
                    else:
                        print(f"     타입: {header[:4]}")
                
                success_count += 1
                results.append({
                    'url': link_info['url'],
                    'success': True,
                    'filename': filepath.name,
                    'size': actual_size
                })
                
            else:
                print(f"  ⚠️  파일이 너무 큼 (10MB 초과), 건너뜀")
                failed_count += 1
                
        except Exception as e:
            print(f"  ❌ 다운로드 실패: {str(e)[:100]}")
            failed_count += 1
            results.append({
                'url': link_info['url'],
                'success': False,
                'error': str(e)[:100]
            })
    
    # 3. 결과 요약
    print("\n" + "="*50)
    print("다운로드 테스트 결과")
    print("="*50)
    print(f"성공: {success_count}개")
    print(f"실패: {failed_count}개")
    
    # 결과 저장
    with open('download_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def test_specific_resources():
    """알려진 리소스 직접 테스트"""
    
    print("\n" + "="*50)
    print("특정 리소스 다운로드 테스트")
    print("="*50)
    
    # Copernicus에서 제공하는 것으로 알려진 리소스들
    known_resources = [
        {
            'name': 'Copernicus Marine Toolbox Documentation',
            'url': 'https://help.marine.copernicus.eu/en/collections/4060068-copernicus-marine-toolbox',
            'type': 'html'
        },
        {
            'name': 'Product User Manual',
            'url': 'https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024/description',
            'type': 'html'
        }
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    for resource in known_resources:
        print(f"\n테스트: {resource['name']}")
        print(f"  URL: {resource['url'][:80]}...")
        
        try:
            response = session.get(resource['url'], timeout=15)
            print(f"  상태: {response.status_code}")
            
            if response.status_code == 200:
                # 컨텐츠 타입 확인
                content_type = response.headers.get('content-type', '')
                print(f"  타입: {content_type}")
                
                # HTML에서 다운로드 링크 찾기
                if 'html' in content_type:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # PDF, ZIP 등 다운로드 링크 찾기
                    download_links = soup.find_all('a', href=lambda x: x and any(ext in x.lower() for ext in ['.pdf', '.zip', '.ipynb', 'download']))
                    
                    if download_links:
                        print(f"  ✅ {len(download_links)}개 다운로드 링크 발견")
                        for link in download_links[:3]:
                            href = link.get('href', '')
                            text = link.get_text(strip=True)[:50]
                            print(f"     - {text}")
                    else:
                        print(f"  ℹ️  다운로드 링크 없음")
                        
        except Exception as e:
            print(f"  ❌ 에러: {str(e)[:100]}")

def test_download_with_enhanced_scraper():
    """향상된 스크래퍼로 실제 다운로드 테스트"""
    
    print("\n" + "="*50)
    print("향상된 스크래퍼 모듈 테스트")
    print("="*50)
    
    try:
        # 향상된 스크래퍼 임포트 시도
        from scrape_copernicus_enhanced import ParallelDownloader, CacheManager
        
        print("✅ 향상된 스크래퍼 모듈 로드 성공")
        
        # 캐시 매니저 테스트
        cache_dir = Path('test_cache')
        cache_manager = CacheManager(cache_dir)
        print(f"✅ 캐시 매니저 초기화 (캐시 디렉토리: {cache_dir})")
        
        # 병렬 다운로더 테스트
        downloader = ParallelDownloader(max_workers=3, cache_manager=cache_manager)
        print(f"✅ 병렬 다운로더 초기화 (워커: 3개)")
        
        # 테스트 다운로드
        test_url = "https://marine.copernicus.eu/robots.txt"
        test_file = Path('test_downloads/robots.txt')
        test_file.parent.mkdir(exist_ok=True)
        
        print(f"\n테스트 다운로드: {test_url}")
        result = downloader.download_file(test_url, test_file)
        
        if result['success']:
            print(f"✅ 다운로드 성공")
            print(f"   크기: {result['size']} bytes")
            print(f"   캐시 사용: {result['cached']}")
        else:
            print(f"❌ 다운로드 실패: {result['error']}")
            
    except ImportError as e:
        print(f"⚠️  향상된 스크래퍼 모듈 로드 실패: {e}")
        print("   기본 스크래퍼를 사용하세요.")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    print("Copernicus Marine Service 실제 다운로드 테스트\n")
    
    # 1. 실제 다운로드 테스트
    results = test_real_downloads()
    
    # 2. 특정 리소스 테스트
    test_specific_resources()
    
    # 3. 향상된 스크래퍼 테스트
    test_download_with_enhanced_scraper()
    
    print("\n" + "="*50)
    print("모든 테스트 완료!")
    print("="*50)
    
    # 다운로드된 파일 목록
    download_dir = Path('test_real_downloads')
    if download_dir.exists():
        files = list(download_dir.glob('*'))
        if files:
            print(f"\n다운로드된 파일들 ({len(files)}개):")
            for f in files:
                size_kb = f.stat().st_size / 1024
                print(f"  - {f.name} ({size_kb:.2f} KB)")