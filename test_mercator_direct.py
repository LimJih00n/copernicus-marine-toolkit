#!/usr/bin/env python3
"""
Mercator Ocean 직접 다운로드 테스트
실제 다운로드 가능한지 확인
"""

import requests
import time
from pathlib import Path

def test_mercator_downloads():
    """Mercator Ocean 공유 링크 직접 테스트"""
    
    print("="*60)
    print("Mercator Ocean 직접 다운로드 테스트")
    print("="*60)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # 사용자가 제공한 실제 링크들
    test_links = [
        "https://atlas.mercator-ocean.fr/s/ZqtwdLNzoQH55JE",
        "https://atlas.mercator-ocean.fr/s/WCM44bp3bFc63PB",
        "https://atlas.mercator-ocean.fr/s/Cf8imxcnmYaAZYL",
        "https://atlas.mercator-ocean.fr/s/oM2SaXder35GbwW"
    ]
    
    download_dir = Path('mercator_downloads')
    download_dir.mkdir(exist_ok=True)
    
    success_count = 0
    
    for link in test_links:
        share_id = link.split('/')[-1]
        print(f"\n테스트: {share_id}")
        print("-" * 40)
        
        # 여러 다운로드 방법 시도
        methods = [
            (f"{link}/download", "직접 /download"),
            (f"{link}?dl=1", "?dl=1 파라미터"),
            (link, "원본 링크")
        ]
        
        for url, method in methods:
            print(f"  시도: {method}")
            print(f"  URL: {url}")
            
            try:
                # HEAD 요청으로 먼저 확인
                head = session.head(url, allow_redirects=True, timeout=10)
                print(f"  상태: {head.status_code}")
                
                # 리다이렉트 확인
                if head.url != url:
                    print(f"  리다이렉트: {head.url[:60]}...")
                
                content_type = head.headers.get('content-type', '')
                content_length = head.headers.get('content-length', '0')
                
                print(f"  타입: {content_type}")
                
                if content_length != '0':
                    size_mb = int(content_length) / (1024 * 1024)
                    print(f"  크기: {size_mb:.2f} MB")
                
                # ZIP 파일이거나 octet-stream인 경우 다운로드
                if any(x in content_type.lower() for x in ['zip', 'octet-stream', 'x-zip']):
                    print(f"  ✓ 다운로드 가능한 파일!")
                    
                    # 실제 다운로드 (작은 파일만)
                    if int(content_length) < 50 * 1024 * 1024:  # 50MB 이하
                        print(f"  다운로드 중...")
                        response = session.get(url, stream=True, timeout=30)
                        
                        filename = f"{share_id}.zip"
                        filepath = download_dir / filename
                        
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        actual_size = filepath.stat().st_size / (1024 * 1024)
                        print(f"  ✓ 다운로드 완료: {filename} ({actual_size:.2f} MB)")
                        
                        # ZIP 파일 검증
                        with open(filepath, 'rb') as f:
                            header = f.read(4)
                            if header.startswith(b'PK'):
                                print(f"  ✓ 유효한 ZIP 파일")
                                success_count += 1
                            else:
                                print(f"  ? 파일 헤더: {header}")
                    else:
                        print(f"  ⚠ 파일이 너무 큼 (50MB 초과)")
                        success_count += 1  # 다운로드 가능함을 확인
                    
                    break  # 성공했으므로 다른 방법 시도 안함
                    
                elif 'html' in content_type.lower():
                    print(f"  HTML 페이지")
                    
                    # HTML 내용 확인
                    if content_length != '0' and int(content_length) < 1024 * 1024:
                        response = session.get(url, timeout=10)
                        
                        # 다운로드 링크 찾기
                        if 'download' in response.text.lower():
                            print(f"  HTML에 download 키워드 발견")
                            
                            # 실제 다운로드 URL 패턴 찾기
                            import re
                            download_patterns = re.findall(r'href="([^"]*download[^"]*)"', response.text, re.I)
                            if download_patterns:
                                print(f"  다운로드 링크 발견: {len(download_patterns)}개")
                                for pattern in download_patterns[:3]:
                                    print(f"    - {pattern[:60]}...")
                else:
                    print(f"  기타 타입")
                    
            except requests.exceptions.Timeout:
                print(f"  ✗ 타임아웃")
            except Exception as e:
                print(f"  ✗ 에러: {str(e)[:50]}")
            
            time.sleep(1)  # 요청 간 딜레이
    
    print("\n" + "="*60)
    print(f"결과: {success_count}/{len(test_links)} 다운로드 가능")
    print("="*60)
    
    # 다운로드된 파일 목록
    if download_dir.exists():
        files = list(download_dir.glob('*'))
        if files:
            print("\n다운로드된 파일:")
            for f in files:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  - {f.name} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    test_mercator_downloads()