#!/usr/bin/env python3
"""
Download found resources from smart_scraping_results.json
"""

import json
import requests
from pathlib import Path

def download_resources():
    # 결과 파일 읽기
    with open('smart_scraping_results.json', 'r') as f:
        data = json.load(f)
    
    resources = data['resources']
    
    print("="*60)
    print("찾은 리소스 다운로드")
    print("="*60)
    
    # 다운로드 디렉토리 생성
    download_dir = Path('copernicus_downloads')
    download_dir.mkdir(exist_ok=True)
    
    # 첫 번째 작은 파일만 다운로드 (테스트용)
    # 나머지는 너무 크므로 (6GB, 258MB)
    target_resource = resources[0]  # rms_sla.zip (32KB)
    
    print(f"\n다운로드: {target_resource['filename']}")
    print(f"크기: {target_resource['size'] / 1024:.1f} KB")
    print(f"URL: {target_resource['url']}")
    
    filepath = download_dir / target_resource['filename']
    
    if filepath.exists():
        print(f"이미 존재: {filepath}")
        return
    
    try:
        print("다운로드 중...")
        response = requests.get(target_resource['url'], stream=True, timeout=60)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        actual_size = filepath.stat().st_size / 1024
        print(f"✓ 다운로드 완료: {actual_size:.1f} KB")
        print(f"저장 위치: {filepath}")
        
        # ZIP 파일 내용 확인
        import zipfile
        if zipfile.is_zipfile(filepath):
            print("\nZIP 파일 내용:")
            with zipfile.ZipFile(filepath, 'r') as zf:
                for info in zf.filelist:
                    print(f"  - {info.filename} ({info.file_size} bytes)")
        
    except Exception as e:
        print(f"✗ 다운로드 실패: {e}")

if __name__ == "__main__":
    download_resources()