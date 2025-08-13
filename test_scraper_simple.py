#!/usr/bin/env python3
"""
Simple Scraper Test - Copernicus Marine Service
간단한 스크래핑 테스트 (requests와 BeautifulSoup만 사용)
"""

import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time

def test_simple_scraping():
    """간단한 스크래핑 테스트 - JavaScript 없는 콘텐츠만"""
    
    print("="*50)
    print("Copernicus Marine Service 스크래핑 테스트")
    print("="*50)
    
    # 테스트할 URL들
    test_urls = [
        "https://marine.copernicus.eu/services/user-learning-services/tutorials",
        "https://marine.copernicus.eu/",
        "https://data.marine.copernicus.eu/products"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    results = {}
    
    for url in test_urls:
        print(f"\n테스트 URL: {url}")
        print("-" * 40)
        
        try:
            # HTTP 요청
            response = session.get(url, timeout=10)
            print(f"✅ 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                # HTML 파싱
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 페이지 정보 추출
                title = soup.find('title')
                if title:
                    print(f"✅ 페이지 제목: {title.text.strip()[:50]}...")
                
                # 튜토리얼 관련 링크 찾기
                tutorial_links = []
                
                # 다양한 패턴으로 링크 찾기
                patterns = [
                    soup.find_all('a', href=lambda x: x and 'tutorial' in x.lower()),
                    soup.find_all('a', href=lambda x: x and 'notebook' in x.lower()),
                    soup.find_all('a', href=lambda x: x and '.ipynb' in x.lower()),
                    soup.find_all('a', href=lambda x: x and 'learn' in x.lower()),
                    soup.find_all('a', href=lambda x: x and 'training' in x.lower()),
                ]
                
                for pattern_links in patterns:
                    for link in pattern_links[:5]:  # 각 패턴당 최대 5개
                        href = link.get('href', '')
                        text = link.get_text(strip=True)[:50]
                        if href and href not in [l['href'] for l in tutorial_links]:
                            tutorial_links.append({
                                'href': href,
                                'text': text
                            })
                
                print(f"✅ 발견된 관련 링크: {len(tutorial_links)}개")
                
                # 처음 5개 링크 표시
                for i, link in enumerate(tutorial_links[:5], 1):
                    print(f"   {i}. {link['text'][:30]}...")
                    print(f"      URL: {link['href'][:60]}...")
                
                # 다운로드 가능한 파일 찾기
                file_extensions = ['.ipynb', '.nc', '.csv', '.json', '.zip', '.pdf']
                downloadable = []
                
                for ext in file_extensions:
                    links = soup.find_all('a', href=lambda x: x and ext in x.lower())
                    for link in links[:3]:
                        href = link.get('href', '')
                        if href:
                            downloadable.append({
                                'type': ext,
                                'url': href,
                                'text': link.get_text(strip=True)[:30]
                            })
                
                if downloadable:
                    print(f"\n✅ 다운로드 가능한 파일: {len(downloadable)}개")
                    for file in downloadable[:5]:
                        print(f"   - {file['type']}: {file['text']}")
                
                # 결과 저장
                results[url] = {
                    'success': True,
                    'title': title.text.strip() if title else None,
                    'tutorial_links': len(tutorial_links),
                    'downloadable_files': len(downloadable),
                    'sample_links': tutorial_links[:3]
                }
                
            else:
                results[url] = {
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                }
                
        except requests.RequestException as e:
            print(f"❌ 요청 실패: {str(e)}")
            results[url] = {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            print(f"❌ 파싱 실패: {str(e)}")
            results[url] = {
                'success': False,
                'error': str(e)
            }
    
    # 테스트 결과 저장
    print("\n" + "="*50)
    print("테스트 결과 요약")
    print("="*50)
    
    success_count = sum(1 for r in results.values() if r.get('success'))
    print(f"성공: {success_count}/{len(results)} 페이지")
    
    # JSON 파일로 저장
    output_file = Path('scraper_test_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과 저장: {output_file}")
    
    return results

def test_download_sample():
    """샘플 파일 다운로드 테스트"""
    print("\n" + "="*50)
    print("샘플 다운로드 테스트")
    print("="*50)
    
    # 테스트용 샘플 URL (공개 데이터)
    test_downloads = [
        {
            'name': 'Copernicus Marine 메인 페이지',
            'url': 'https://marine.copernicus.eu/',
            'type': 'html'
        }
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    download_dir = Path('test_downloads')
    download_dir.mkdir(exist_ok=True)
    
    for item in test_downloads:
        print(f"\n다운로드 시도: {item['name']}")
        
        try:
            response = session.get(item['url'], stream=True, timeout=30)
            response.raise_for_status()
            
            # 컨텐츠 타입 확인
            content_type = response.headers.get('content-type', '')
            print(f"  컨텐츠 타입: {content_type}")
            
            # 파일 크기 확인
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                print(f"  파일 크기: {size_mb:.2f} MB")
            
            # HTML인 경우 처음 1000자만 저장
            if 'html' in content_type.lower():
                filename = download_dir / f"sample_{item['type']}.html"
                content = response.text[:1000]
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ 저장됨: {filename} (처음 1000자)")
            
        except Exception as e:
            print(f"  ❌ 실패: {str(e)}")

def test_specific_tutorial_sources():
    """특정 튜토리얼 소스 테스트"""
    print("\n" + "="*50)
    print("알려진 튜토리얼 소스 테스트")
    print("="*50)
    
    # 알려진 Copernicus 튜토리얼/학습 자료 URL들
    known_sources = [
        "https://marine.copernicus.eu/services/user-learning-services",
        "https://marine.copernicus.eu/services/use-cases",
        "https://help.marine.copernicus.eu/",
        "https://resources.marine.copernicus.eu/documents"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    for url in known_sources:
        print(f"\n체크: {url}")
        try:
            response = session.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"  ✅ 접근 가능 (상태: {response.status_code})")
                # 실제 URL이 다른 경우 표시
                if response.url != url:
                    print(f"  → 리다이렉트: {response.url}")
            else:
                print(f"  ⚠️  상태 코드: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 접근 실패: {str(e)}")

if __name__ == "__main__":
    print("Copernicus Marine Service 스크래핑 테스트 시작\n")
    
    # 1. 기본 스크래핑 테스트
    results = test_simple_scraping()
    
    # 2. 다운로드 테스트
    test_download_sample()
    
    # 3. 특정 소스 테스트
    test_specific_tutorial_sources()
    
    print("\n" + "="*50)
    print("모든 테스트 완료!")
    print("="*50)