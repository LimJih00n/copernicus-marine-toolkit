#!/usr/bin/env python3
"""
Copernicus 튜토리얼 페이지 실제 테스트
실제로 무엇이 있는지 확인
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path

def deep_test_copernicus():
    """Copernicus 튜토리얼 페이지 심층 분석"""
    
    print("="*60)
    print("Copernicus 튜토리얼 페이지 심층 분석")
    print("="*60)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # 메인 튜토리얼 페이지
    main_url = "https://marine.copernicus.eu/services/user-learning-services/tutorials"
    
    print(f"\n1. 메인 페이지 분석: {main_url}")
    print("-" * 40)
    
    try:
        response = session.get(main_url, timeout=15)
        print(f"상태 코드: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 페이지 구조 분석
        print(f"페이지 제목: {soup.title.text if soup.title else 'N/A'}")
        
        # 모든 링크 추출
        all_links = soup.find_all('a', href=True)
        print(f"총 링크 수: {len(all_links)}")
        
        # 튜토리얼 관련 링크 필터링
        tutorial_links = []
        download_links = []
        external_links = []
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 카테고리 분류
            if any(keyword in href.lower() for keyword in ['tutorial', 'training', 'learn', 'example']):
                tutorial_links.append({
                    'url': href,
                    'text': text[:50],
                    'type': 'tutorial'
                })
            
            if any(keyword in href.lower() for keyword in ['download', '.zip', '.ipynb', '.pdf']):
                download_links.append({
                    'url': href,
                    'text': text[:50],
                    'type': 'download'
                })
            
            if href.startswith('http') and 'marine.copernicus.eu' not in href:
                external_links.append({
                    'url': href,
                    'text': text[:50],
                    'type': 'external'
                })
        
        print(f"\n튜토리얼 링크: {len(tutorial_links)}개")
        for i, link in enumerate(tutorial_links[:5], 1):
            print(f"  {i}. {link['text']}")
            print(f"     URL: {link['url'][:60]}...")
        
        print(f"\n다운로드 링크: {len(download_links)}개")
        for i, link in enumerate(download_links[:5], 1):
            print(f"  {i}. {link['text']}")
            print(f"     URL: {link['url'][:60]}...")
        
        print(f"\n외부 링크: {len(external_links)}개")
        for i, link in enumerate(external_links[:5], 1):
            print(f"  {i}. {link['text']}")
            print(f"     URL: {link['url'][:60]}...")
        
        # 특정 패턴 검색
        print("\n2. 특정 패턴 검색")
        print("-" * 40)
        
        # data 속성 확인
        data_attrs = soup.find_all(attrs={'data-download': True})
        data_attrs.extend(soup.find_all(attrs={'data-href': True}))
        data_attrs.extend(soup.find_all(attrs={'data-url': True}))
        
        if data_attrs:
            print(f"데이터 속성 발견: {len(data_attrs)}개")
            for elem in data_attrs[:3]:
                print(f"  - {elem.name}: {elem.attrs}")
        
        # 버튼이나 카드 요소 확인
        buttons = soup.find_all(['button', 'a'], class_=re.compile(r'download|btn|button', re.I))
        if buttons:
            print(f"\n다운로드 버튼 발견: {len(buttons)}개")
            for btn in buttons[:3]:
                print(f"  - {btn.get_text(strip=True)[:30]}")
                if btn.get('href'):
                    print(f"    href: {btn['href'][:50]}")
                if btn.get('onclick'):
                    print(f"    onclick: {btn['onclick'][:50]}")
        
        # 개별 튜토리얼 페이지 확인
        print("\n3. 개별 튜토리얼 페이지 확인")
        print("-" * 40)
        
        # 찾은 튜토리얼 링크 중 일부를 실제로 방문
        for link in tutorial_links[:3]:
            url = link['url']
            if not url.startswith('http'):
                url = f"https://marine.copernicus.eu{url}"
            
            print(f"\n체크: {link['text']}")
            print(f"  URL: {url[:60]}...")
            
            try:
                sub_response = session.get(url, timeout=10)
                if sub_response.status_code == 200:
                    sub_soup = BeautifulSoup(sub_response.text, 'html.parser')
                    
                    # 다운로드 가능한 리소스 찾기
                    resources = []
                    
                    # 직접 파일 링크
                    file_links = sub_soup.find_all('a', href=re.compile(r'\.(ipynb|zip|pdf|nc)', re.I))
                    for fl in file_links:
                        resources.append({
                            'type': 'direct',
                            'url': fl['href'],
                            'text': fl.get_text(strip=True)[:30]
                        })
                    
                    # iframe (embedded content)
                    iframes = sub_soup.find_all('iframe')
                    for iframe in iframes:
                        if iframe.get('src'):
                            resources.append({
                                'type': 'iframe',
                                'url': iframe['src'],
                                'text': 'Embedded content'
                            })
                    
                    # 외부 플랫폼 링크
                    external = sub_soup.find_all('a', href=re.compile(r'github|gitlab|zenodo|drive\.google', re.I))
                    for ext in external:
                        resources.append({
                            'type': 'external',
                            'url': ext['href'],
                            'text': ext.get_text(strip=True)[:30]
                        })
                    
                    if resources:
                        print(f"  ✓ {len(resources)}개 리소스 발견")
                        for r in resources[:3]:
                            print(f"    - [{r['type']}] {r['text']}")
                            print(f"      {r['url'][:50]}...")
                    else:
                        print(f"  ✗ 리소스 없음")
                        
            except Exception as e:
                print(f"  ✗ 접근 실패: {str(e)[:50]}")
        
        # 결과 저장
        result = {
            'main_page': main_url,
            'total_links': len(all_links),
            'tutorial_links': len(tutorial_links),
            'download_links': len(download_links),
            'external_links': len(external_links),
            'samples': {
                'tutorials': tutorial_links[:5],
                'downloads': download_links[:5],
                'external': external_links[:5]
            }
        }
        
        with open('copernicus_deep_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n분석 결과 저장: copernicus_deep_analysis.json")
        
    except Exception as e:
        print(f"에러: {e}")

def test_specific_resources():
    """알려진 특정 리소스 테스트"""
    
    print("\n" + "="*60)
    print("특정 리소스 직접 테스트")
    print("="*60)
    
    # 가능한 튜토리얼 URL 패턴들
    test_urls = [
        "https://marine.copernicus.eu/services/user-learning-services/arctic-ocean-training-2022",
        "https://marine.copernicus.eu/services/user-learning-services/mediterranean-sea-analysis",
        "https://marine.copernicus.eu/services/user-learning-services/baltic-sea-training",
        "https://marine.copernicus.eu/services/user-learning-services/black-sea-biogeochemistry",
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    for url in test_urls:
        print(f"\n테스트: {url.split('/')[-1]}")
        
        try:
            response = session.head(url, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                print(f"  ✓ 페이지 존재 (상태: {response.status_code})")
                
                # 실제 콘텐츠 확인
                full_response = session.get(url, timeout=10)
                soup = BeautifulSoup(full_response.text, 'html.parser')
                
                # 다운로드 링크 찾기
                downloads = soup.find_all('a', href=re.compile(r'download|\.zip|\.ipynb', re.I))
                if downloads:
                    print(f"  ✓ {len(downloads)}개 다운로드 링크 발견")
                    for d in downloads[:2]:
                        print(f"    - {d.get_text(strip=True)[:30]}")
                        
            elif response.status_code == 404:
                print(f"  ✗ 페이지 없음")
            else:
                print(f"  ? 상태 코드: {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ 에러: {str(e)[:50]}")

if __name__ == "__main__":
    # 심층 분석
    deep_test_copernicus()
    
    # 특정 리소스 테스트
    test_specific_resources()
    
    print("\n" + "="*60)
    print("분석 완료!")
    print("="*60)