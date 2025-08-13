#!/usr/bin/env python3
"""
Find Jupyter notebooks from various sources
더 많은 소스에서 노트북 찾기
"""

import requests
import json
from pathlib import Path
import re

def find_copernicus_notebooks():
    """다양한 소스에서 Copernicus 관련 노트북 찾기"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    found_notebooks = []
    
    print("="*60)
    print("Copernicus Marine 노트북 검색")
    print("="*60)
    
    # 1. Copernicus Marine Toolbox 공식 저장소 (새로운 URL)
    print("\n1. 공식 저장소 검색...")
    official_repos = [
        # 가능한 조직명들
        ("copernicus-marine", "toolbox"),
        ("cmems", "notebooks"),
        ("cmems-mod", "notebooks"),
        ("mercator-ocean", "notebooks"),
        ("mercator-ocean", "copernicus"),
        ("mercator-ocean-international", "notebooks"),
    ]
    
    for org, repo in official_repos:
        api_url = f"https://api.github.com/repos/{org}/{repo}"
        print(f"  체크: {org}/{repo}")
        
        try:
            response = session.get(api_url, timeout=5)
            if response.status_code == 200:
                print(f"    ✓ 저장소 발견!")
                # contents API로 파일 목록 가져오기
                contents_url = f"{api_url}/contents"
                search_for_notebooks(session, contents_url, found_notebooks, org, repo)
        except:
            pass
    
    # 2. GitHub 코드 검색 (더 구체적인 검색어)
    print("\n2. GitHub 코드 검색...")
    search_queries = [
        "copernicus marine extension:ipynb",
        "cmems extension:ipynb", 
        "copernicus ocean python extension:ipynb",
        "mercator ocean extension:ipynb"
    ]
    
    for query in search_queries:
        print(f"  검색: {query}")
        
        try:
            # GitHub 검색 API
            search_url = "https://api.github.com/search/code"
            params = {
                'q': query,
                'per_page': 5,
                'sort': 'indexed',
                'order': 'desc'
            }
            
            response = session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                for item in items:
                    # raw URL 생성
                    html_url = item.get('html_url', '')
                    if html_url and '.ipynb' in html_url:
                        raw_url = convert_to_raw_url(html_url)
                        
                        found_notebooks.append({
                            'name': item.get('name', 'notebook.ipynb'),
                            'url': raw_url,
                            'repo': item.get('repository', {}).get('full_name', 'unknown'),
                            'path': item.get('path', ''),
                            'size': item.get('size', 0)
                        })
                        
                print(f"    ✓ {len(items)} 노트북 발견")
                
            elif response.status_code == 403:
                print(f"    ⚠ API 제한")
                break
                
        except Exception as e:
            print(f"    ✗ 에러: {str(e)[:50]}")
    
    # 3. 알려진 교육 자료 저장소
    print("\n3. 알려진 교육 저장소...")
    known_repos = [
        # 해양 데이터 분석 교육 자료
        "https://api.github.com/repos/pangeo-data/pangeo-tutorial/contents",
        "https://api.github.com/repos/oceanhackweek/ohw-tutorials/contents",
        "https://api.github.com/repos/euroargodev/argopy/contents/docs/examples",
        "https://api.github.com/repos/xarray-contrib/xarray-tutorial/contents/workshops",
    ]
    
    for repo_url in known_repos:
        repo_name = repo_url.split('/repos/')[1].split('/contents')[0]
        print(f"  체크: {repo_name}")
        
        try:
            response = session.get(repo_url, timeout=10)
            if response.status_code == 200:
                items = response.json()
                notebook_count = 0
                
                for item in items:
                    if item.get('name', '').endswith('.ipynb'):
                        found_notebooks.append({
                            'name': item.get('name'),
                            'url': item.get('download_url'),
                            'repo': repo_name,
                            'path': item.get('path'),
                            'size': item.get('size', 0)
                        })
                        notebook_count += 1
                        
                if notebook_count > 0:
                    print(f"    ✓ {notebook_count} 노트북 발견")
                    
        except:
            pass
    
    # 4. Binder/nbviewer에서 인기 있는 노트북
    print("\n4. 추가 소스 검색...")
    
    # MyBinder 예제들
    binder_examples = [
        "https://raw.githubusercontent.com/binder-examples/requirements/master/index.ipynb",
        "https://raw.githubusercontent.com/binder-examples/conda/master/index.ipynb",
    ]
    
    for url in binder_examples:
        if 'ocean' in url.lower() or 'marine' in url.lower() or 'copernicus' in url.lower():
            name = url.split('/')[-1]
            found_notebooks.append({
                'name': name,
                'url': url,
                'repo': 'binder-examples',
                'path': name,
                'size': 0
            })
    
    # 결과 정리
    print("\n" + "="*60)
    print("검색 결과")
    print("="*60)
    print(f"총 {len(found_notebooks)}개 노트북 발견")
    
    # 중복 제거
    unique_notebooks = []
    seen_urls = set()
    
    for nb in found_notebooks:
        if nb['url'] not in seen_urls:
            seen_urls.add(nb['url'])
            unique_notebooks.append(nb)
    
    print(f"중복 제거 후: {len(unique_notebooks)}개")
    
    # 결과 저장
    with open('found_notebooks.json', 'w', encoding='utf-8') as f:
        json.dump(unique_notebooks, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과 저장: found_notebooks.json")
    
    # 상위 10개 출력
    if unique_notebooks:
        print("\n발견된 노트북 (상위 10개):")
        for i, nb in enumerate(unique_notebooks[:10], 1):
            print(f"  {i}. {nb['name']}")
            print(f"     저장소: {nb['repo']}")
            print(f"     크기: {nb['size'] / 1024:.1f} KB")
    
    return unique_notebooks

def search_for_notebooks(session, contents_url, found_list, org, repo, path="", depth=0, max_depth=2):
    """재귀적으로 노트북 검색"""
    
    if depth > max_depth:
        return
    
    try:
        response = session.get(contents_url, timeout=10)
        if response.status_code == 200:
            items = response.json()
            
            for item in items:
                if item.get('type') == 'file' and item.get('name', '').endswith('.ipynb'):
                    found_list.append({
                        'name': item.get('name'),
                        'url': item.get('download_url'),
                        'repo': f"{org}/{repo}",
                        'path': item.get('path'),
                        'size': item.get('size', 0)
                    })
                elif item.get('type') == 'dir' and depth < max_depth:
                    # 관련 디렉토리만 탐색
                    dir_name = item.get('name', '').lower()
                    if any(keyword in dir_name for keyword in ['notebook', 'example', 'tutorial', 'demo']):
                        sub_url = item.get('url')
                        if sub_url:
                            search_for_notebooks(session, sub_url, found_list, org, repo, 
                                               item.get('path'), depth + 1, max_depth)
    except:
        pass

def convert_to_raw_url(github_url):
    """GitHub URL을 raw URL로 변환"""
    
    raw_url = github_url
    raw_url = raw_url.replace('github.com', 'raw.githubusercontent.com')
    raw_url = raw_url.replace('/blob/', '/')
    
    return raw_url

def download_notebooks(notebooks, max_downloads=3):
    """노트북 다운로드"""
    
    if not notebooks:
        print("다운로드할 노트북이 없습니다.")
        return
    
    print("\n" + "="*60)
    print(f"노트북 다운로드 (최대 {max_downloads}개)")
    print("="*60)
    
    download_dir = Path('copernicus_downloads')
    download_dir.mkdir(exist_ok=True)
    
    session = requests.Session()
    
    # 크기가 작은 것부터 다운로드
    notebooks_sorted = sorted(notebooks, key=lambda x: x.get('size', 0))
    
    downloaded = 0
    for nb in notebooks_sorted:
        if downloaded >= max_downloads:
            break
            
        filename = nb['name']
        url = nb['url']
        
        if not url:
            continue
        
        filepath = download_dir / filename
        
        # 이미 존재하면 스킵
        if filepath.exists():
            print(f"⚠ 이미 존재: {filename}")
            continue
        
        print(f"\n다운로드: {filename}")
        print(f"  URL: {url[:60]}...")
        
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            size_kb = filepath.stat().st_size / 1024
            print(f"  ✓ 완료: {size_kb:.1f} KB")
            downloaded += 1
            
        except Exception as e:
            print(f"  ✗ 실패: {str(e)[:50]}")
    
    print(f"\n총 {downloaded}개 노트북 다운로드 완료")

if __name__ == "__main__":
    notebooks = find_copernicus_notebooks()
    
    if notebooks:
        # 자동으로 상위 3개 다운로드
        download_notebooks(notebooks, max_downloads=3)