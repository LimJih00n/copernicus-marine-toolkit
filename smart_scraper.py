#!/usr/bin/env python3
"""
Smart Scraper for Copernicus Marine Service
직접적인 GitHub 저장소와 알려진 소스에서 .ipynb, .zip 파일 찾기
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict
import time

class SmartCopernicusScraper:
    """스마트 스크래퍼 - 알려진 소스 중심"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.found_resources = []
        
    def find_github_notebooks(self) -> List[Dict]:
        """GitHub에서 Copernicus 관련 노트북 찾기"""
        
        print("\n1. GitHub 저장소 검색...")
        print("-" * 40)
        
        resources = []
        
        # 알려진 Copernicus 관련 GitHub 조직/저장소
        github_repos = [
            # Copernicus Marine 공식
            "CopernicusMarineService/copernicus-marine-toolbox",
            "mercator-ocean/copernicus-marine-toolbox-gallery",
            
            # 가능한 저장소들
            "CopernicusMarineService/notebooks",
            "CopernicusMarineService/examples",
            "CopernicusMarineService/tutorials",
            "mercator-ocean/notebooks",
            
            # 알려진 튜토리얼 저장소
            "oceanhackweek/ohw20-tutorials",
            "euroargodev/argopy",
        ]
        
        for repo in github_repos:
            print(f"  체크: {repo}")
            
            # GitHub API 사용 (더 빠르고 정확)
            api_url = f"https://api.github.com/repos/{repo}/contents"
            
            try:
                # 저장소 루트 확인
                response = self.session.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    # 재귀적으로 파일 찾기 (너무 깊지 않게)
                    self._search_github_files(api_url, resources, max_depth=2)
                    print(f"    ✓ {len(resources)} 파일 발견")
                elif response.status_code == 404:
                    print(f"    - 저장소 없음")
                    
            except Exception as e:
                print(f"    ✗ 에러: {str(e)[:50]}")
                
        # 추가: GitHub 검색 API로 Copernicus 노트북 찾기
        search_url = "https://api.github.com/search/code"
        search_queries = [
            "copernicus marine filename:*.ipynb",
            "cmems filename:*.ipynb",
            "copernicus ocean filename:*.ipynb"
        ]
        
        for query in search_queries[:1]:  # API 제한 때문에 1개만
            try:
                params = {
                    'q': query,
                    'per_page': 10
                }
                response = self.session.get(search_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('items', [])[:5]:  # 상위 5개만
                        # raw URL로 변환
                        html_url = item.get('html_url', '')
                        if html_url:
                            raw_url = html_url.replace('github.com', 'raw.githubusercontent.com')
                            raw_url = raw_url.replace('/blob/', '/')
                            
                            resources.append({
                                'url': raw_url,
                                'filename': item.get('name', 'notebook.ipynb'),
                                'type': 'notebook',
                                'source': 'github_search',
                                'description': f"From {item.get('repository', {}).get('full_name', 'unknown')}"
                            })
                            
            except:
                pass
                
        return resources
        
    def _search_github_files(self, api_url: str, resources: List[Dict], 
                            depth: int = 0, max_depth: int = 2):
        """GitHub API로 재귀적 파일 검색"""
        
        if depth > max_depth:
            return
            
        try:
            response = self.session.get(api_url, timeout=10)
            if response.status_code != 200:
                return
                
            items = response.json()
            
            for item in items:
                name = item.get('name', '')
                item_type = item.get('type', '')
                
                # 파일인 경우
                if item_type == 'file':
                    # .ipynb, .zip 파일 확인
                    if name.endswith('.ipynb') or name.endswith('.zip'):
                        resources.append({
                            'url': item.get('download_url', ''),
                            'filename': name,
                            'type': 'notebook' if name.endswith('.ipynb') else 'archive',
                            'source': 'github',
                            'size': item.get('size', 0),
                            'description': item.get('path', '')
                        })
                        
                # 디렉토리인 경우
                elif item_type == 'dir' and depth < max_depth:
                    # 관련 디렉토리만 탐색
                    relevant_dirs = ['notebooks', 'examples', 'tutorials', 'demos', 
                                   'training', 'exercises', 'data', 'use-cases']
                    
                    if any(keyword in name.lower() for keyword in relevant_dirs):
                        # 재귀 탐색
                        sub_url = item.get('url', '')
                        if sub_url:
                            self._search_github_files(sub_url, resources, depth + 1, max_depth)
                            
        except:
            pass
            
    def find_direct_downloads(self) -> List[Dict]:
        """Copernicus 웹사이트에서 직접 다운로드 링크 찾기"""
        
        print("\n2. Copernicus 웹사이트 스캔...")
        print("-" * 40)
        
        resources = []
        
        # 스캔할 페이지들
        pages = [
            "https://marine.copernicus.eu/services/user-learning-services/tutorials",
            "https://marine.copernicus.eu/services/use-cases",
            "https://help.marine.copernicus.eu/en/collections/4060068-copernicus-marine-toolbox",
        ]
        
        for page_url in pages:
            print(f"  스캔: {page_url[:60]}...")
            
            try:
                response = self.session.get(page_url, timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 모든 링크 확인
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # 절대 URL로 변환
                    absolute_url = urljoin(page_url, href)
                    
                    # 다운로드 가능한 파일 패턴
                    if any(ext in href.lower() for ext in ['.ipynb', '.zip', '.tar', '.gz']):
                        resources.append({
                            'url': absolute_url,
                            'filename': href.split('/')[-1],
                            'type': 'file',
                            'source': 'copernicus',
                            'description': text[:100]
                        })
                        
                    # GitHub 링크 발견
                    elif 'github.com' in href:
                        # GitHub 링크를 raw 형식으로 변환
                        if '.ipynb' in href:
                            raw_url = href.replace('github.com', 'raw.githubusercontent.com')
                            raw_url = raw_url.replace('/blob/', '/')
                            resources.append({
                                'url': raw_url,
                                'filename': href.split('/')[-1],
                                'type': 'notebook',
                                'source': 'copernicus_github_link',
                                'description': text[:100]
                            })
                            
                print(f"    ✓ {len(resources)} 링크 발견")
                
            except Exception as e:
                print(f"    ✗ 에러: {str(e)[:50]}")
                
        return resources
        
    def find_zenodo_resources(self) -> List[Dict]:
        """Zenodo에서 Copernicus 관련 데이터셋 찾기"""
        
        print("\n3. Zenodo 데이터셋 검색...")
        print("-" * 40)
        
        resources = []
        
        # Zenodo API
        zenodo_api = "https://zenodo.org/api/records"
        
        try:
            params = {
                'q': 'copernicus marine',
                'size': 10,
                'type': 'dataset'
            }
            
            response = self.session.get(zenodo_api, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for hit in data.get('hits', {}).get('hits', [])[:5]:
                    files = hit.get('files', [])
                    
                    for file in files:
                        key = file.get('key', '')
                        if any(ext in key.lower() for ext in ['.ipynb', '.zip', '.tar']):
                            resources.append({
                                'url': file.get('links', {}).get('self', ''),
                                'filename': key,
                                'type': 'dataset',
                                'source': 'zenodo',
                                'size': file.get('size', 0),
                                'description': hit.get('metadata', {}).get('title', '')[:100]
                            })
                            
                print(f"    ✓ {len(resources)} 파일 발견")
                
        except Exception as e:
            print(f"    ✗ 에러: {str(e)[:50]}")
            
        return resources
        
    def run(self):
        """스크래핑 실행"""
        
        print("="*60)
        print("Smart Copernicus Scraper")
        print("="*60)
        
        all_resources = []
        
        # 1. GitHub 검색
        github_resources = self.find_github_notebooks()
        all_resources.extend(github_resources)
        
        # 2. 직접 다운로드 링크
        direct_resources = self.find_direct_downloads()
        all_resources.extend(direct_resources)
        
        # 3. Zenodo 검색
        zenodo_resources = self.find_zenodo_resources()
        all_resources.extend(zenodo_resources)
        
        # 중복 제거
        unique_resources = []
        seen_urls = set()
        
        for resource in all_resources:
            url = resource.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_resources.append(resource)
                
        # 결과 요약
        print("\n" + "="*60)
        print("스크래핑 결과")
        print("="*60)
        print(f"총 발견: {len(unique_resources)}개 리소스")
        
        # 타입별 집계
        by_type = {}
        for r in unique_resources:
            t = r.get('type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
            
        print("\n타입별:")
        for t, count in by_type.items():
            print(f"  {t}: {count}개")
            
        # 소스별 집계
        by_source = {}
        for r in unique_resources:
            s = r.get('source', 'unknown')
            by_source[s] = by_source.get(s, 0) + 1
            
        print("\n소스별:")
        for s, count in by_source.items():
            print(f"  {s}: {count}개")
            
        # 결과 저장
        with open('smart_scraping_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(unique_resources),
                'by_type': by_type,
                'by_source': by_source,
                'resources': unique_resources
            }, f, indent=2, ensure_ascii=False)
            
        print(f"\n결과 저장: smart_scraping_results.json")
        
        # 샘플 출력
        if unique_resources:
            print("\n발견된 리소스 샘플:")
            for i, r in enumerate(unique_resources[:10], 1):
                print(f"  {i}. {r.get('filename', 'unknown')}")
                print(f"     소스: {r.get('source', 'unknown')}")
                print(f"     URL: {r.get('url', '')[:60]}...")
                
        return unique_resources
        
    def download_resources(self, resources: List[Dict], max_files: int = 5):
        """리소스 다운로드 (테스트용으로 제한)"""
        
        print("\n" + "="*60)
        print(f"리소스 다운로드 (최대 {max_files}개)")
        print("="*60)
        
        download_dir = Path('copernicus_downloads')
        download_dir.mkdir(exist_ok=True)
        
        # .ipynb와 .zip 파일만 필터링
        target_resources = [
            r for r in resources 
            if r.get('filename', '').endswith(('.ipynb', '.zip'))
        ][:max_files]
        
        if not target_resources:
            print("다운로드할 .ipynb 또는 .zip 파일이 없습니다.")
            return
            
        for i, resource in enumerate(target_resources, 1):
            filename = resource.get('filename', f'file_{i}')
            url = resource.get('url', '')
            
            if not url:
                continue
                
            print(f"\n[{i}/{len(target_resources)}] {filename}")
            print(f"  URL: {url[:60]}...")
            
            filepath = download_dir / filename
            
            # 이미 존재하면 스킵
            if filepath.exists():
                print(f"  ⚠ 이미 존재")
                continue
                
            try:
                response = self.session.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # 다운로드
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
                size_kb = filepath.stat().st_size / 1024
                print(f"  ✓ 완료: {size_kb:.1f} KB")
                
            except Exception as e:
                print(f"  ✗ 실패: {str(e)[:50]}")


if __name__ == "__main__":
    scraper = SmartCopernicusScraper()
    resources = scraper.run()
    
    # 다운로드 여부 확인
    if resources:
        answer = input("\n샘플 다운로드를 진행하시겠습니까? (y/n): ")
        if answer.lower() == 'y':
            scraper.download_resources(resources, max_files=5)