#!/usr/bin/env python3
"""
Deep Scraper for Copernicus Marine Service
깊이 있는 크롤링으로 실제 .ipynb, .zip 파일 찾기
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse, unquote
from typing import List, Dict, Set, Tuple
import hashlib

class DeepCopernicusScraper:
    """깊이 있는 크롤링을 수행하는 스크래퍼"""
    
    def __init__(self, max_depth: int = 3):
        """
        Parameters:
            max_depth: 최대 크롤링 깊이
        """
        self.max_depth = max_depth
        self.visited_urls = set()
        self.found_files = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # 다운로드할 파일 확장자
        self.target_extensions = [
            '.ipynb', '.zip', '.tar', '.gz', '.tar.gz', '.7z',
            '.nc', '.netcdf', '.hdf', '.hdf5', '.grib', '.grib2'
        ]
        
        # 알려진 파일 호스팅 패턴
        self.file_hosting_patterns = [
            r'github\.com/.*?/raw/',
            r'github\.com/.*?/releases/download/',
            r'gitlab\.com/.*?/-/raw/',
            r'bitbucket\.org/.*?/raw/',
            r'drive\.google\.com/.*?/download',
            r'dropbox\.com/.*?\?dl=1',
            r'zenodo\.org/record/',
            r'figshare\.com/.*?/download',
            r'data\.marine\.copernicus\.eu/.*?/download',
            r'resources\.marine\.copernicus\.eu/.*?/download',
            r'mercator-ocean\.fr/.*?/download',
        ]
        
    def is_downloadable_file(self, url: str) -> bool:
        """URL이 다운로드 가능한 파일인지 확인"""
        url_lower = url.lower()
        
        # 확장자 확인
        for ext in self.target_extensions:
            if ext in url_lower:
                return True
                
        # 다운로드 키워드 확인
        download_keywords = ['download', 'export', 'get', 'fetch', 'retrieve']
        for keyword in download_keywords:
            if keyword in url_lower:
                return True
                
        # 파일 호스팅 패턴 확인
        for pattern in self.file_hosting_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
                
        return False
        
    def extract_file_info(self, url: str, link_text: str = "") -> Dict:
        """파일 정보 추출"""
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        
        # 파일명 추출
        filename = path.split('/')[-1] if '/' in path else path
        
        # 파일명이 없거나 너무 짧으면 URL 해시 사용
        if not filename or len(filename) < 3:
            filename = hashlib.md5(url.encode()).hexdigest()[:8]
            
        # 확장자 추출
        extension = None
        for ext in self.target_extensions:
            if ext in filename.lower():
                extension = ext
                break
                
        if not extension and 'download' in url.lower():
            # HEAD 요청으로 실제 파일 타입 확인 시도
            try:
                head = self.session.head(url, allow_redirects=True, timeout=5)
                content_type = head.headers.get('content-type', '')
                content_disposition = head.headers.get('content-disposition', '')
                
                # Content-Disposition에서 파일명 추출
                if 'filename=' in content_disposition:
                    match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^\s]+)', content_disposition)
                    if match:
                        filename = match.group(1).strip('"\'')
                        
                # Content-Type에서 확장자 추측
                if 'zip' in content_type:
                    extension = '.zip'
                elif 'notebook' in content_type or 'json' in content_type:
                    extension = '.ipynb'
                elif 'netcdf' in content_type:
                    extension = '.nc'
                    
            except:
                pass
                
        return {
            'url': url,
            'filename': filename,
            'extension': extension,
            'link_text': link_text[:100],
            'source_type': self.classify_source(url)
        }
        
    def classify_source(self, url: str) -> str:
        """URL 소스 분류"""
        if 'github.com' in url:
            return 'github'
        elif 'gitlab.com' in url:
            return 'gitlab'
        elif 'copernicus' in url:
            return 'copernicus'
        elif 'mercator' in url:
            return 'mercator'
        elif 'zenodo.org' in url:
            return 'zenodo'
        else:
            return 'other'
            
    def find_github_resources(self, content: str, base_url: str) -> List[Dict]:
        """GitHub 저장소 링크에서 리소스 찾기"""
        resources = []
        
        # GitHub 저장소 패턴
        github_patterns = [
            r'https?://github\.com/[\w\-]+/[\w\-]+(?:/tree/[\w\-]+)?',
            r'https?://github\.com/[\w\-]+/[\w\-]+/blob/[\w\-]+/[\w\-/]+\.ipynb',
        ]
        
        for pattern in github_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # blob을 raw로 변환
                raw_url = match.replace('/blob/', '/raw/')
                
                # 저장소 메인 페이지인 경우, 일반적인 위치 확인
                if '/tree/' not in match and '/blob/' not in match:
                    # 일반적인 노트북 위치들
                    common_paths = [
                        '/raw/main/notebooks/',
                        '/raw/master/notebooks/',
                        '/raw/main/examples/',
                        '/raw/master/examples/',
                        '/raw/main/',
                        '/raw/master/',
                    ]
                    
                    repo_base = match.rstrip('/')
                    for path in common_paths:
                        # API를 통해 파일 목록 가져오기 시도
                        api_url = repo_base.replace('github.com', 'api.github.com/repos') + '/contents'
                        if 'notebooks' in path:
                            api_url += '/notebooks'
                        elif 'examples' in path:
                            api_url += '/examples'
                            
                        try:
                            api_response = self.session.get(api_url, timeout=5)
                            if api_response.status_code == 200:
                                files = api_response.json()
                                for file in files:
                                    if file.get('name', '').endswith('.ipynb'):
                                        resources.append({
                                            'url': file.get('download_url', ''),
                                            'filename': file.get('name', ''),
                                            'extension': '.ipynb',
                                            'link_text': f"GitHub: {file.get('name', '')}",
                                            'source_type': 'github'
                                        })
                        except:
                            pass
                            
                # 직접 .ipynb 링크인 경우
                elif '.ipynb' in match:
                    resources.append(self.extract_file_info(raw_url, "GitHub Notebook"))
                    
        return resources
        
    def deep_crawl(self, url: str, depth: int = 0) -> List[Dict]:
        """깊이 우선 크롤링"""
        
        if depth > self.max_depth or url in self.visited_urls:
            return []
            
        self.visited_urls.add(url)
        found_resources = []
        
        print(f"{'  ' * depth}크롤링 (깊이 {depth}): {url[:80]}...")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content = response.text
            
            # 1. 직접적인 파일 링크 찾기
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                if not href:
                    continue
                    
                # 절대 URL로 변환
                absolute_url = urljoin(url, href)
                
                # 다운로드 가능한 파일인지 확인
                if self.is_downloadable_file(absolute_url):
                    file_info = self.extract_file_info(absolute_url, link.get_text(strip=True))
                    if file_info['extension']:  # 확장자가 확인된 경우만
                        found_resources.append(file_info)
                        print(f"{'  ' * depth}  ✓ 발견: {file_info['filename']}")
                        
            # 2. GitHub 리소스 찾기
            github_resources = self.find_github_resources(content, url)
            found_resources.extend(github_resources)
            
            # 3. JavaScript에 숨겨진 URL 찾기
            script_patterns = [
                r'["\']url["\']\s*:\s*["\']([^"\']+\.(?:ipynb|zip|tar|gz))["\']',
                r'download["\']?\s*:\s*["\']([^"\']+)["\']',
                r'href\s*=\s*["\']([^"\']+\.(?:ipynb|zip|tar|gz))["\']',
            ]
            
            for pattern in script_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    absolute_url = urljoin(url, match)
                    if absolute_url not in [r['url'] for r in found_resources]:
                        file_info = self.extract_file_info(absolute_url, "JavaScript Link")
                        if file_info['extension']:
                            found_resources.append(file_info)
                            
            # 4. 데이터 속성에서 URL 찾기
            data_links = soup.find_all(attrs={'data-download': True})
            data_links.extend(soup.find_all(attrs={'data-href': True}))
            data_links.extend(soup.find_all(attrs={'data-url': True}))
            
            for elem in data_links:
                for attr in ['data-download', 'data-href', 'data-url']:
                    if elem.has_attr(attr):
                        data_url = elem[attr]
                        absolute_url = urljoin(url, data_url)
                        if self.is_downloadable_file(absolute_url):
                            file_info = self.extract_file_info(absolute_url, "Data Attribute Link")
                            if file_info['extension']:
                                found_resources.append(file_info)
                                
            # 5. 하위 페이지 크롤링 (관련 페이지만)
            if depth < self.max_depth:
                # 관련 키워드가 있는 링크만 따라가기
                relevant_keywords = [
                    'tutorial', 'notebook', 'example', 'demo', 'training',
                    'learn', 'education', 'material', 'resource', 'download',
                    'data', 'dataset', 'file', 'github', 'gitlab', 'code'
                ]
                
                for link in all_links[:20]:  # 최대 20개 링크만
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True).lower()
                    
                    # 관련 키워드 확인
                    if any(keyword in link_text or keyword in href.lower() for keyword in relevant_keywords):
                        absolute_url = urljoin(url, href)
                        
                        # 외부 도메인 제외
                        if urlparse(absolute_url).netloc != urlparse(url).netloc:
                            continue
                            
                        # 이미 방문한 URL 제외
                        if absolute_url not in self.visited_urls:
                            # 재귀적으로 크롤링
                            sub_resources = self.deep_crawl(absolute_url, depth + 1)
                            found_resources.extend(sub_resources)
                            
        except Exception as e:
            print(f"{'  ' * depth}  ✗ 에러: {str(e)[:50]}")
            
        return found_resources
        
    def scrape_copernicus_resources(self) -> Dict:
        """Copernicus Marine Service 리소스 스크래핑"""
        
        print("="*60)
        print("Copernicus Marine Service Deep Scraping")
        print("="*60)
        
        # 시작 URL들
        start_urls = [
            "https://marine.copernicus.eu/services/user-learning-services/tutorials",
            "https://marine.copernicus.eu/services/user-learning-services",
            "https://help.marine.copernicus.eu/en",
            "https://marine.copernicus.eu/services/use-cases",
            # 알려진 GitHub 저장소들
            "https://github.com/CopernicusMarineService",
            "https://github.com/mercator-ocean",
        ]
        
        all_resources = []
        
        for url in start_urls:
            print(f"\n시작점: {url}")
            print("-" * 40)
            resources = self.deep_crawl(url, 0)
            all_resources.extend(resources)
            
        # 중복 제거
        unique_resources = []
        seen_urls = set()
        
        for resource in all_resources:
            if resource['url'] not in seen_urls:
                seen_urls.add(resource['url'])
                unique_resources.append(resource)
                
        # 결과 정리
        results = {
            'total_found': len(unique_resources),
            'by_extension': {},
            'by_source': {},
            'resources': unique_resources
        }
        
        # 확장자별 집계
        for resource in unique_resources:
            ext = resource.get('extension', 'unknown')
            results['by_extension'][ext] = results['by_extension'].get(ext, 0) + 1
            
            source = resource.get('source_type', 'unknown')
            results['by_source'][source] = results['by_source'].get(source, 0) + 1
            
        return results
        
    def download_resources(self, resources: List[Dict], output_dir: str = "downloads") -> List[Dict]:
        """리소스 다운로드"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print("\n" + "="*60)
        print("리소스 다운로드")
        print("="*60)
        
        download_results = []
        
        for i, resource in enumerate(resources, 1):
            print(f"\n[{i}/{len(resources)}] {resource['filename']}")
            print(f"  URL: {resource['url'][:80]}...")
            
            try:
                # 파일명 정리
                safe_filename = re.sub(r'[^\w\-_\.]', '_', resource['filename'])
                if not safe_filename:
                    safe_filename = f"file_{i}"
                    
                # 확장자 추가
                if resource['extension'] and not safe_filename.endswith(resource['extension']):
                    safe_filename += resource['extension']
                    
                filepath = output_path / safe_filename
                
                # 이미 존재하면 스킵
                if filepath.exists():
                    print(f"  ⚠ 이미 존재: {filepath}")
                    download_results.append({
                        'resource': resource,
                        'status': 'skipped',
                        'filepath': str(filepath)
                    })
                    continue
                    
                # 다운로드
                response = self.session.get(resource['url'], stream=True, timeout=30)
                response.raise_for_status()
                
                # 파일 저장
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 진행 상황 표시
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\r  다운로드: {progress:.1f}%", end='')
                                
                print(f"\n  ✓ 완료: {filepath} ({downloaded / 1024:.1f} KB)")
                
                download_results.append({
                    'resource': resource,
                    'status': 'success',
                    'filepath': str(filepath),
                    'size': downloaded
                })
                
            except Exception as e:
                print(f"  ✗ 실패: {str(e)[:100]}")
                download_results.append({
                    'resource': resource,
                    'status': 'failed',
                    'error': str(e)
                })
                
        return download_results


def main():
    """메인 실행 함수"""
    
    # 스크래퍼 초기화
    scraper = DeepCopernicusScraper(max_depth=2)
    
    # 리소스 찾기
    results = scraper.scrape_copernicus_resources()
    
    # 결과 출력
    print("\n" + "="*60)
    print("스크래핑 결과")
    print("="*60)
    print(f"총 발견: {results['total_found']}개 리소스")
    
    print("\n확장자별:")
    for ext, count in results['by_extension'].items():
        print(f"  {ext}: {count}개")
        
    print("\n소스별:")
    for source, count in results['by_source'].items():
        print(f"  {source}: {count}개")
        
    # 결과 저장
    with open('deep_scraping_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n결과 저장: deep_scraping_results.json")
    
    # .ipynb와 .zip 파일만 필터링
    target_resources = [
        r for r in results['resources']
        if r.get('extension') in ['.ipynb', '.zip', '.tar', '.gz', '.tar.gz']
    ]
    
    if target_resources:
        print(f"\n다운로드 대상: {len(target_resources)}개 파일")
        
        # 사용자 확인
        print("\n다운로드할 파일 목록:")
        for i, resource in enumerate(target_resources[:10], 1):  # 처음 10개만 표시
            print(f"  {i}. {resource['filename']} ({resource['source_type']})")
            
        if len(target_resources) > 10:
            print(f"  ... 외 {len(target_resources) - 10}개")
            
        # 다운로드 실행
        answer = input("\n다운로드를 진행하시겠습니까? (y/n): ")
        if answer.lower() == 'y':
            download_results = scraper.download_resources(target_resources)
            
            # 다운로드 결과 요약
            success_count = sum(1 for r in download_results if r['status'] == 'success')
            failed_count = sum(1 for r in download_results if r['status'] == 'failed')
            skipped_count = sum(1 for r in download_results if r['status'] == 'skipped')
            
            print("\n" + "="*60)
            print("다운로드 완료")
            print("="*60)
            print(f"성공: {success_count}개")
            print(f"실패: {failed_count}개")
            print(f"스킵: {skipped_count}개")
    else:
        print("\n⚠ 다운로드할 .ipynb 또는 .zip 파일을 찾지 못했습니다.")
        print("GitHub 저장소나 다른 소스를 직접 확인해보세요.")


if __name__ == "__main__":
    main()