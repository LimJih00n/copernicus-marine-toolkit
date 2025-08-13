#!/usr/bin/env python3
"""
Enhanced Copernicus Marine Service Tutorial Scraper
병렬 다운로드와 캐시 시스템이 추가된 향상된 버전
"""

import os
import re
import json
import time
import hashlib
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class CacheManager:
    """다운로드 캐시 관리 클래스"""
    
    def __init__(self, cache_dir: Path, expire_days: int = 30):
        """
        Parameters:
            cache_dir: 캐시 디렉토리 경로
            expire_days: 캐시 만료 일수
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.expire_days = expire_days
        self.index_file = self.cache_dir / 'cache_index.json'
        self.index = self._load_index()
        
    def _load_index(self) -> Dict:
        """캐시 인덱스 로드"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}
        
    def _save_index(self):
        """캐시 인덱스 저장"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
            
    def _get_cache_key(self, url: str) -> str:
        """URL에서 캐시 키 생성"""
        return hashlib.md5(url.encode()).hexdigest()
        
    def is_cached(self, url: str) -> bool:
        """캐시 존재 여부 확인"""
        cache_key = self._get_cache_key(url)
        
        if cache_key not in self.index:
            return False
            
        # 만료 확인
        cache_info = self.index[cache_key]
        cached_date = datetime.fromisoformat(cache_info['date'])
        if datetime.now() - cached_date > timedelta(days=self.expire_days):
            # 만료된 캐시 삭제
            self.remove_cache(url)
            return False
            
        # 파일 존재 확인
        cache_file = self.cache_dir / cache_info['filename']
        return cache_file.exists()
        
    def get_cached_file(self, url: str) -> Optional[Path]:
        """캐시된 파일 경로 반환"""
        if not self.is_cached(url):
            return None
            
        cache_key = self._get_cache_key(url)
        cache_info = self.index[cache_key]
        return self.cache_dir / cache_info['filename']
        
    def add_to_cache(self, url: str, source_file: Path) -> Path:
        """파일을 캐시에 추가"""
        cache_key = self._get_cache_key(url)
        cache_filename = f"{cache_key}_{source_file.name}"
        cache_file = self.cache_dir / cache_filename
        
        # 파일 복사
        import shutil
        shutil.copy2(source_file, cache_file)
        
        # 인덱스 업데이트
        self.index[cache_key] = {
            'url': url,
            'filename': cache_filename,
            'original_name': source_file.name,
            'date': datetime.now().isoformat(),
            'size': cache_file.stat().st_size
        }
        self._save_index()
        
        return cache_file
        
    def remove_cache(self, url: str):
        """캐시 제거"""
        cache_key = self._get_cache_key(url)
        
        if cache_key in self.index:
            cache_info = self.index[cache_key]
            cache_file = self.cache_dir / cache_info['filename']
            
            if cache_file.exists():
                cache_file.unlink()
                
            del self.index[cache_key]
            self._save_index()
            
    def clear_expired(self):
        """만료된 캐시 정리"""
        expired_keys = []
        
        for cache_key, cache_info in self.index.items():
            cached_date = datetime.fromisoformat(cache_info['date'])
            if datetime.now() - cached_date > timedelta(days=self.expire_days):
                expired_keys.append(cache_key)
                
        for key in expired_keys:
            url = self.index[key]['url']
            self.remove_cache(url)
            
        print(f"만료된 캐시 {len(expired_keys)}개 정리 완료")


class ParallelDownloader:
    """병렬 다운로드 관리 클래스"""
    
    def __init__(self, max_workers: int = 5, cache_manager: Optional[CacheManager] = None):
        """
        Parameters:
            max_workers: 최대 동시 다운로드 스레드 수
            cache_manager: 캐시 매니저 인스턴스
        """
        self.max_workers = max_workers
        self.cache_manager = cache_manager
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """세션 생성"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 연결 재사용을 위한 어댑터 설정
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.max_workers,
            pool_maxsize=self.max_workers * 2,
            max_retries=3
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
        
    def download_file(self, url: str, filepath: Path, use_cache: bool = True) -> Dict:
        """
        단일 파일 다운로드
        
        Parameters:
            url: 다운로드 URL
            filepath: 저장할 파일 경로
            use_cache: 캐시 사용 여부
            
        Returns:
            다운로드 결과 정보
        """
        result = {
            'url': url,
            'filepath': str(filepath),
            'success': False,
            'cached': False,
            'size': 0,
            'error': None
        }
        
        try:
            # 캐시 확인
            if use_cache and self.cache_manager and self.cache_manager.is_cached(url):
                cached_file = self.cache_manager.get_cached_file(url)
                if cached_file:
                    # 캐시에서 복사
                    import shutil
                    shutil.copy2(cached_file, filepath)
                    result['success'] = True
                    result['cached'] = True
                    result['size'] = filepath.stat().st_size
                    return result
                    
            # 다운로드 수행
            response = self.session.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            # 파일 저장
            total_size = int(response.headers.get('content-length', 0))
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            result['success'] = True
            result['size'] = filepath.stat().st_size
            
            # 캐시에 추가
            if use_cache and self.cache_manager and result['success']:
                self.cache_manager.add_to_cache(url, filepath)
                
        except Exception as e:
            result['error'] = str(e)
            
        return result
        
    def download_batch(self, download_tasks: List[Tuple[str, Path]], use_cache: bool = True) -> List[Dict]:
        """
        병렬 배치 다운로드
        
        Parameters:
            download_tasks: (URL, 저장경로) 튜플 리스트
            use_cache: 캐시 사용 여부
            
        Returns:
            다운로드 결과 리스트
        """
        results = []
        total_tasks = len(download_tasks)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 다운로드 작업 제출
            future_to_task = {
                executor.submit(self.download_file, url, path, use_cache): (url, path)
                for url, path in download_tasks
            }
            
            # 진행 표시와 함께 결과 수집
            with tqdm(total=total_tasks, desc="병렬 다운로드") as pbar:
                for future in as_completed(future_to_task):
                    result = future.result()
                    results.append(result)
                    
                    # 진행 상태 업데이트
                    status = "캐시" if result['cached'] else "다운로드"
                    if result['success']:
                        size_mb = result['size'] / (1024 * 1024)
                        pbar.set_postfix({
                            'status': status,
                            'size': f'{size_mb:.1f}MB'
                        })
                    else:
                        pbar.set_postfix({'status': '실패'})
                        
                    pbar.update(1)
                    
        return results


class EnhancedCopernicusScraper:
    """향상된 코페르니쿠스 스크래퍼"""
    
    def __init__(self, base_url: str = None, output_dir: str = "tutorials", 
                 max_workers: int = 5, use_cache: bool = True):
        """
        Parameters:
            base_url: 코페르니쿠스 튜토리얼 페이지 URL
            output_dir: 다운로드할 디렉토리 경로
            max_workers: 최대 동시 다운로드 수
            use_cache: 캐시 시스템 사용 여부
        """
        self.base_url = base_url or "https://marine.copernicus.eu/services/user-learning-services/tutorials"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 캐시 매니저 설정
        self.cache_manager = None
        if use_cache:
            cache_dir = self.output_dir / '.cache'
            self.cache_manager = CacheManager(cache_dir)
            self.cache_manager.clear_expired()  # 시작 시 만료된 캐시 정리
            
        # 병렬 다운로더 설정
        self.downloader = ParallelDownloader(max_workers, self.cache_manager)
        
        self.metadata = []
        self.driver = None
        
    def setup_selenium(self):
        """Selenium WebDriver 설정"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def close_selenium(self):
        """Selenium WebDriver 종료"""
        if self.driver:
            self.driver.quit()
            
    def get_page_content(self, url: str) -> str:
        """페이지 콘텐츠 가져오기"""
        try:
            response = self.downloader.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
        except:
            pass
            
        if not self.driver:
            self.setup_selenium()
            
        self.driver.get(url)
        time.sleep(3)
        return self.driver.page_source
        
    def sanitize_filename(self, filename: str) -> str:
        """파일명 정제"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.replace(' ', '_')
        filename = re.sub(r'_+', '_', filename)
        filename = filename.strip('_')
        return filename[:50] if len(filename) > 50 else filename
        
    def extract_tutorial_links(self) -> List[Dict]:
        """튜토리얼 링크 추출"""
        print(f"페이지 분석 중: {self.base_url}")
        content = self.get_page_content(self.base_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        tutorials = []
        tutorial_id = 1
        
        patterns = [
            ('a', {'href': re.compile(r'tutorial|notebook|\.ipynb', re.I)}),
            ('div', {'class': re.compile(r'tutorial|card|item', re.I)}),
            ('li', {'class': re.compile(r'tutorial|resource', re.I)}),
        ]
        
        for tag, attrs in patterns:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                link = None
                if tag == 'a':
                    link = elem.get('href')
                else:
                    link_elem = elem.find('a')
                    if link_elem:
                        link = link_elem.get('href')
                
                if not link:
                    continue
                    
                if not link.startswith('http'):
                    link = f"https://marine.copernicus.eu{link}"
                
                title = elem.get_text(strip=True)[:100] if elem.get_text() else f"Tutorial_{tutorial_id}"
                title = self.sanitize_filename(title)
                
                if not any(t['url'] == link for t in tutorials):
                    tutorials.append({
                        'id': tutorial_id,
                        'title': title,
                        'url': link,
                        'folder': f"{tutorial_id:02d}_{title}"
                    })
                    tutorial_id += 1
                    
        print(f"발견된 튜토리얼: {len(tutorials)}개")
        return tutorials
        
    def extract_resources(self, tutorial_url: str) -> List[Dict]:
        """리소스 추출"""
        resources = []
        content = self.get_page_content(tutorial_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        file_patterns = [
            r'\.ipynb', r'\.nc', r'\.csv', r'\.json',
            r'\.py', r'\.zip', r'\.tar', r'\.pdf'
        ]
        
        pattern = '|'.join(file_patterns)
        links = soup.find_all('a', href=re.compile(pattern, re.I))
        
        for link in links:
            href = link.get('href')
            if not href:
                continue
                
            if not href.startswith('http'):
                if href.startswith('/'):
                    href = f"https://marine.copernicus.eu{href}"
                else:
                    href = f"{tutorial_url}/{href}"
                    
            filename = href.split('/')[-1].split('?')[0]
            if not filename:
                filename = 'unknown_file'
                
            resources.append({
                'url': href,
                'filename': filename,
                'type': filename.split('.')[-1] if '.' in filename else 'unknown'
            })
            
        return resources
        
    def process_tutorial(self, tutorial: Dict) -> Dict:
        """튜토리얼 처리 (병렬 다운로드 사용)"""
        print(f"\n처리 중: {tutorial['title']}")
        
        tutorial_dir = self.output_dir / tutorial['folder']
        tutorial_dir.mkdir(exist_ok=True)
        
        resources = self.extract_resources(tutorial['url'])
        print(f"  발견된 리소스: {len(resources)}개")
        
        # 다운로드 작업 준비
        download_tasks = []
        for resource in resources:
            filepath = tutorial_dir / resource['filename']
            
            # 이미 존재하는 파일은 스킵
            if filepath.exists() and filepath.stat().st_size > 0:
                print(f"  스킵 (이미 존재): {resource['filename']}")
                continue
                
            download_tasks.append((resource['url'], filepath))
            
        # 병렬 다운로드 실행
        if download_tasks:
            print(f"  병렬 다운로드 시작: {len(download_tasks)}개 파일")
            results = self.downloader.download_batch(download_tasks)
            
            # 결과 집계
            success_count = sum(1 for r in results if r['success'])
            cached_count = sum(1 for r in results if r['cached'])
            failed_count = sum(1 for r in results if not r['success'])
            
            print(f"  완료: 성공 {success_count}개 (캐시 {cached_count}개), 실패 {failed_count}개")
            
            return {
                'tutorial': tutorial,
                'resources': results,
                'success': success_count,
                'cached': cached_count,
                'failed': failed_count
            }
        else:
            return {
                'tutorial': tutorial,
                'resources': [],
                'success': 0,
                'cached': 0,
                'failed': 0
            }
            
    def save_metadata(self):
        """메타데이터 저장"""
        metadata_file = self.output_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scrape_date': datetime.now().isoformat(),
                'base_url': self.base_url,
                'cache_enabled': self.cache_manager is not None,
                'tutorials': self.metadata
            }, f, indent=2, ensure_ascii=False)
            
        print(f"\n메타데이터 저장: {metadata_file}")
        
    def run(self):
        """스크래핑 실행"""
        print("="*50)
        print("향상된 코페르니쿠스 튜토리얼 스크래퍼")
        print(f"병렬 다운로드: {self.downloader.max_workers}개 스레드")
        print(f"캐시 시스템: {'활성화' if self.cache_manager else '비활성화'}")
        print("="*50)
        
        try:
            tutorials = self.extract_tutorial_links()
            
            if not tutorials:
                print("튜토리얼을 찾을 수 없습니다.")
                return
                
            for tutorial in tqdm(tutorials, desc="전체 진행"):
                result = self.process_tutorial(tutorial)
                self.metadata.append(result)
                
            self.save_metadata()
            
            # 결과 요약
            total_success = sum(m['success'] for m in self.metadata)
            total_cached = sum(m['cached'] for m in self.metadata)
            total_failed = sum(m['failed'] for m in self.metadata)
            
            print("\n" + "="*50)
            print("스크래핑 완료!")
            print(f"처리된 튜토리얼: {len(tutorials)}개")
            print(f"다운로드 성공: {total_success}개 (캐시 사용: {total_cached}개)")
            print(f"다운로드 실패: {total_failed}개")
            
            if self.cache_manager:
                cache_size = sum(f.stat().st_size for f in self.cache_manager.cache_dir.glob('*') if f.is_file())
                print(f"캐시 크기: {cache_size / (1024*1024):.1f}MB")
            print("="*50)
            
        finally:
            self.close_selenium()


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='향상된 코페르니쿠스 튜토리얼 스크래퍼')
    parser.add_argument('--url', type=str, help='튜토리얼 페이지 URL',
                       default="https://marine.copernicus.eu/services/user-learning-services/tutorials")
    parser.add_argument('--output', type=str, help='출력 디렉토리', default='tutorials')
    parser.add_argument('--workers', type=int, help='최대 동시 다운로드 수', default=5)
    parser.add_argument('--no-cache', action='store_true', help='캐시 비활성화')
    
    args = parser.parse_args()
    
    scraper = EnhancedCopernicusScraper(
        base_url=args.url,
        output_dir=args.output,
        max_workers=args.workers,
        use_cache=not args.no_cache
    )
    scraper.run()


if __name__ == "__main__":
    main()