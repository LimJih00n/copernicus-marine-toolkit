#!/usr/bin/env python3
"""
간단한 데모 - 자동으로 링크 찾고 다운로드
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time

def auto_find_and_download():
    """완전 자동 다운로드 데모"""
    
    print("🚀 Copernicus Marine 자동 다운로드 시작")
    print("="*50)
    
    # 1. 자동으로 메인 페이지 접속
    print("\n1️⃣ Copernicus 튜토리얼 페이지 접속 중...")
    url = "https://marine.copernicus.eu/services/user-learning-services/tutorials"
    
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    response = session.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 2. 자동으로 튜토리얼 링크 찾기
    print("2️⃣ 튜토리얼 링크 자동 탐색 중...")
    
    # 'training' 또는 'tutorial' 키워드가 있는 링크 찾기
    tutorial_links = []
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if any(keyword in href.lower() for keyword in ['training', 'arctic', 'baltic', 'africa']):
            if href.startswith('/'):
                full_url = f"https://marine.copernicus.eu{href}"
                tutorial_links.append(full_url)
    
    print(f"   ✓ {len(tutorial_links)}개 튜토리얼 발견")
    
    # 3. 각 튜토리얼에서 Mercator Ocean 링크 찾기
    print("3️⃣ 다운로드 링크 자동 추출 중...")
    
    download_links = []
    for tutorial_url in tutorial_links[:3]:  # 처음 3개만 테스트
        try:
            resp = session.get(tutorial_url, timeout=5)
            sub_soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Mercator Ocean 링크 찾기
            for link in sub_soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'atlas.mercator-ocean.fr/s/' in href:
                    # 자동으로 /download 추가
                    download_url = href if href.endswith('/download') else href + '/download'
                    download_links.append(download_url)
                    print(f"   ✓ 발견: {href.split('/')[-1][:10]}...")
                    break
        except:
            pass
    
    print(f"\n📊 결과:")
    print(f"   - 튜토리얼 페이지: {len(tutorial_links)}개")
    print(f"   - 다운로드 링크: {len(download_links)}개")
    
    # 4. 자동 다운로드
    if download_links:
        print("\n4️⃣ 자동 다운로드 시작...")
        
        download_dir = Path('auto_downloads')
        download_dir.mkdir(exist_ok=True)
        
        for i, url in enumerate(download_links[:1], 1):  # 첫 번째만 실제 다운로드
            print(f"\n다운로드 {i}/{len(download_links[:1])}")
            print(f"URL: {url}")
            
            try:
                # 파일 정보 확인
                head = session.head(url, allow_redirects=True, timeout=10)
                content_type = head.headers.get('content-type', '')
                
                if 'zip' in content_type.lower() or 'octet-stream' in content_type:
                    print("✓ ZIP 파일 확인")
                    
                    # 작은 부분만 다운로드 (데모용)
                    response = session.get(url, stream=True, timeout=10)
                    
                    filename = f"tutorial_{i}.zip"
                    filepath = download_dir / filename
                    
                    # 처음 1MB만 다운로드 (데모)
                    with open(filepath, 'wb') as f:
                        downloaded = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if downloaded > 1024 * 1024:  # 1MB
                                    break
                    
                    size_kb = filepath.stat().st_size / 1024
                    print(f"✓ 다운로드 완료: {filename} ({size_kb:.1f}KB)")
                    
            except Exception as e:
                print(f"✗ 실패: {str(e)[:50]}")
    
    print("\n" + "="*50)
    print("✅ 자동 다운로드 완료!")
    print("\n💡 이것이 자동으로 수행되는 작업입니다:")
    print("   1. 사이트 자동 접속")
    print("   2. 링크 자동 발견")
    print("   3. 파일 자동 다운로드")
    print("   4. 사용자는 실행만 하면 됨!")

if __name__ == "__main__":
    auto_find_and_download()