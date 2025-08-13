#!/usr/bin/env python3
"""
Multi-level Copernicus Scraper
여러 단계를 거쳐 실제 다운로드에 도달하는 스크래퍼
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
import re

class MultiLevelCopernicusScraper:
    """다단계 크롤링 스크래퍼"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.visited = set()
        self.download_links = []
        
    def follow_tutorial_path(self, start_url, max_depth=3):
        """튜토리얼 경로를 따라가며 다운로드 링크 찾기"""
        
        print(f"\n시작 URL: {start_url}")
        print("="*60)
        
        return self._crawl_level(start_url, depth=0, max_depth=max_depth)
        
    def _crawl_level(self, url, depth=0, max_depth=3):
        """재귀적으로 각 레벨 크롤링"""
        
        if depth > max_depth or url in self.visited:
            return []
            
        self.visited.add(url)
        found_resources = []
        
        indent = "  " * depth
        print(f"{indent}레벨 {depth}: {url.split('/')[-1][:50]}")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 직접 다운로드 링크 찾기
            direct_downloads = self._find_direct_downloads(soup, url)
            if direct_downloads:
                print(f"{indent}  ✓ {len(direct_downloads)}개 직접 다운로드 발견")
                found_resources.extend(direct_downloads)
            
            # 2. 다운로드 버튼 찾기
            download_buttons = self._find_download_buttons(soup, url)
            for btn_url in download_buttons:
                print(f"{indent}  → 다운로드 버튼 클릭: {btn_url.split('/')[-1][:30]}")
                sub_resources = self._crawl_level(btn_url, depth + 1, max_depth)
                found_resources.extend(sub_resources)
            
            # 3. 튜토리얼 하위 페이지 찾기
            if depth < max_depth:
                sub_pages = self._find_tutorial_subpages(soup, url)
                for sub_url in sub_pages[:5]:  # 최대 5개 하위 페이지만
                    if sub_url not in self.visited:
                        print(f"{indent}  → 하위 페이지: {sub_url.split('/')[-1][:30]}")
                        sub_resources = self._crawl_level(sub_url, depth + 1, max_depth)
                        found_resources.extend(sub_resources)
            
            # 4. 외부 플랫폼 링크 처리
            external_links = self._find_external_platforms(soup)
            if external_links:
                print(f"{indent}  ✓ {len(external_links)}개 외부 플랫폼 링크")
                for ext in external_links:
                    # Mercator Ocean 특별 처리
                    if 'atlas.mercator-ocean.fr' in ext:
                        # /download 추가
                        if not ext.endswith('/download'):
                            download_url = ext + '/download'
                            # URL에서 공유 ID 추출
                            share_id = ext.split('/')[-1] if '/s/' in ext else ext.split('/')[-2]
                            print(f"{indent}  → Mercator Ocean: {share_id[:30]}/download")
                            found_resources.append({
                                'url': download_url,
                                'type': 'mercator',
                                'source_page': url
                            })
                    else:
                        found_resources.append({
                            'url': ext,
                            'type': 'external',
                            'source_page': url
                        })
            
        except Exception as e:
            print(f"{indent}  ✗ 에러: {str(e)[:50]}")
            
        return found_resources
        
    def _find_direct_downloads(self, soup, base_url):
        """직접 다운로드 가능한 파일 링크 찾기"""
        
        downloads = []
        
        # 파일 확장자 패턴
        file_patterns = [r'\.ipynb', r'\.zip', r'\.tar', r'\.gz', r'\.pdf', r'\.nc']
        
        for pattern in file_patterns:
            links = soup.find_all('a', href=re.compile(pattern, re.I))
            for link in links:
                href = link.get('href', '')
                absolute_url = urljoin(base_url, href)
                
                downloads.append({
                    'url': absolute_url,
                    'filename': href.split('/')[-1],
                    'type': 'direct_file',
                    'text': link.get_text(strip=True)[:50]
                })
                
        return downloads
        
    def _find_download_buttons(self, soup, base_url):
        """다운로드 버튼이나 링크 찾기"""
        
        button_urls = []
        
        # 다운로드 관련 텍스트나 클래스를 가진 요소들
        download_elements = soup.find_all(['a', 'button'], 
                                         text=re.compile(r'download|get|access|retrieve', re.I))
        
        for elem in download_elements:
            href = elem.get('href')
            if href:
                absolute_url = urljoin(base_url, href)
                if absolute_url not in self.visited:
                    button_urls.append(absolute_url)
        
        # class나 id에 download가 포함된 링크
        download_class = soup.find_all('a', class_=re.compile(r'download|btn.*download', re.I))
        for elem in download_class:
            href = elem.get('href')
            if href:
                absolute_url = urljoin(base_url, href)
                if absolute_url not in self.visited:
                    button_urls.append(absolute_url)
                    
        return list(set(button_urls))  # 중복 제거
        
    def _find_tutorial_subpages(self, soup, base_url):
        """튜토리얼 관련 하위 페이지 찾기"""
        
        subpages = []
        base_domain = urlparse(base_url).netloc
        
        # 관련 키워드
        keywords = ['tutorial', 'training', 'exercise', 'example', 'notebook', 'data']
        
        for keyword in keywords:
            links = soup.find_all('a', href=re.compile(keyword, re.I))
            for link in links:
                href = link.get('href', '')
                if href and not href.startswith('#'):
                    absolute_url = urljoin(base_url, href)
                    
                    # 같은 도메인인지 확인
                    if urlparse(absolute_url).netloc == base_domain:
                        subpages.append(absolute_url)
                        
        return list(set(subpages))  # 중복 제거
        
    def _find_external_platforms(self, soup):
        """외부 플랫폼 링크 찾기"""
        
        external = []
        
        # 알려진 플랫폼 패턴
        platforms = [
            r'atlas\.mercator-ocean\.fr',
            r'github\.com',
            r'gitlab\.com',
            r'zenodo\.org',
            r'drive\.google\.com',
            r'dropbox\.com'
        ]
        
        for platform in platforms:
            links = soup.find_all('a', href=re.compile(platform, re.I))
            for link in links:
                href = link.get('href', '')
                if href:
                    external.append(href)
                    
        return list(set(external))
        
    def test_specific_tutorials(self):
        """특정 튜토리얼 테스트"""
        
        print("\n" + "="*60)
        print("특정 튜토리얼 심층 테스트")
        print("="*60)
        
        # 테스트할 URL들
        test_urls = [
            "https://marine.copernicus.eu/services/user-learning-services/tutorials",
            "https://marine.copernicus.eu/services/user-learning-services/arctic-ocean-training-2022-discover-copernicus-marine-service",
            "https://atlas.mercator-ocean.fr/s/ZqtwdLNzoQH55JE"
        ]
        
        all_resources = []
        
        for url in test_urls:
            print(f"\n테스트: {url}")
            print("-"*40)
            
            resources = self.follow_tutorial_path(url, max_depth=2)
            all_resources.extend(resources)
            
            print(f"\n발견된 리소스: {len(resources)}개")
            for r in resources[:5]:
                print(f"  - [{r['type']}] {r.get('filename', r['url'].split('/')[-1][:30])}")
                
        # 중복 제거
        unique_resources = []
        seen_urls = set()
        
        for r in all_resources:
            if r['url'] not in seen_urls:
                seen_urls.add(r['url'])
                unique_resources.append(r)
                
        print("\n" + "="*60)
        print(f"총 발견 리소스: {len(unique_resources)}개")
        print("="*60)
        
        # 타입별 분류
        by_type = {}
        for r in unique_resources:
            t = r.get('type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
            
        print("\n타입별 분류:")
        for t, count in by_type.items():
            print(f"  {t}: {count}개")
            
        # 결과 저장
        with open('multilevel_scraping_results.json', 'w', encoding='utf-8') as f:
            json.dump(unique_resources, f, indent=2, ensure_ascii=False)
            
        print(f"\n결과 저장: multilevel_scraping_results.json")
        
        return unique_resources
        
    def download_found_resources(self, resources, max_downloads=3):
        """발견한 리소스 다운로드 시도"""
        
        print("\n" + "="*60)
        print("리소스 다운로드 시도")
        print("="*60)
        
        download_dir = Path('copernicus_multilevel_downloads')
        download_dir.mkdir(exist_ok=True)
        
        # Mercator Ocean 링크 우선
        mercator_resources = [r for r in resources if r.get('type') == 'mercator']
        
        for i, resource in enumerate(mercator_resources[:max_downloads], 1):
            url = resource['url']
            print(f"\n[{i}] 다운로드 시도")
            print(f"  URL: {url}")
            
            try:
                # HEAD 요청으로 먼저 확인
                head_response = self.session.head(url, allow_redirects=True, timeout=10)
                content_type = head_response.headers.get('content-type', '')
                content_length = head_response.headers.get('content-length', '0')
                
                print(f"  타입: {content_type}")
                if content_length != '0':
                    size_mb = int(content_length) / (1024 * 1024)
                    print(f"  크기: {size_mb:.2f} MB")
                
                # 10MB 이하만 다운로드
                if int(content_length) < 10 * 1024 * 1024 or content_length == '0':
                    response = self.session.get(url, stream=True, timeout=30)
                    response.raise_for_status()
                    
                    # 파일명 결정
                    if 'content-disposition' in response.headers:
                        import re
                        d = response.headers['content-disposition']
                        fname = re.findall('filename="?(.+)"?', d)
                        if fname:
                            filename = fname[0].strip('"')
                        else:
                            filename = f"download_{i}.bin"
                    else:
                        filename = url.split('/')[-2] + '.zip' if 'mercator' in url else f"download_{i}.bin"
                    
                    filepath = download_dir / filename
                    
                    # 다운로드
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    actual_size = filepath.stat().st_size / 1024
                    print(f"  ✓ 성공: {filename} ({actual_size:.1f} KB)")
                    
                    # ZIP 파일인지 확인
                    with open(filepath, 'rb') as f:
                        header = f.read(4)
                        if header.startswith(b'PK'):
                            print(f"  ✓ ZIP 파일 확인")
                        elif header.startswith(b'%PDF'):
                            print(f"  ✓ PDF 파일 확인")
                        else:
                            print(f"  ? 파일 타입: {header}")
                else:
                    print(f"  ⚠ 파일이 너무 큼 (10MB 초과)")
                    
            except Exception as e:
                print(f"  ✗ 실패: {str(e)[:100]}")

if __name__ == "__main__":
    scraper = MultiLevelCopernicusScraper()
    
    # 테스트 실행
    resources = scraper.test_specific_tutorials()
    
    # 다운로드 시도
    if resources:
        scraper.download_found_resources(resources, max_downloads=3)