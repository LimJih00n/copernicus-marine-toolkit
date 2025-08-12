#!/usr/bin/env python3
"""
Copernicus Marine Service Tutorial Scraper
자동으로 코페르니쿠스 해양 서비스의 모든 튜토리얼을 다운로드하는 스크립트
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

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


class CopernicusScraper:
    """코페르니쿠스 튜토리얼 스크래퍼 클래스"""
    
    def __init__(self, base_url: str = None, output_dir: str = "tutorials"):
        """
        Parameters:
            base_url: 코페르니쿠스 튜토리얼 페이지 URL
            output_dir: 다운로드할 디렉토리 경로
        """
        self.base_url = base_url or "https://marine.copernicus.eu/services/user-learning-services/tutorials"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
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
        """
        페이지 콘텐츠 가져오기 (JavaScript 렌더링 처리)
        
        Parameters:
            url: 가져올 페이지 URL
            
        Returns:
            HTML 콘텐츠
        """
        try:
            # 먼저 requests로 시도
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
        except:
            pass
            
        # JavaScript 렌더링이 필요한 경우 Selenium 사용
        if not self.driver:
            self.setup_selenium()
            
        self.driver.get(url)
        time.sleep(3)  # 페이지 로딩 대기
        return self.driver.page_source
        
    def extract_tutorial_links(self) -> List[Dict]:
        """
        메인 페이지에서 튜토리얼 링크 추출
        
        Returns:
            튜토리얼 정보 리스트
        """
        print(f"페이지 분석 중: {self.base_url}")
        content = self.get_page_content(self.base_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        tutorials = []
        tutorial_id = 1
        
        # 다양한 패턴으로 튜토리얼 링크 찾기
        patterns = [
            # Pattern 1: 직접 링크
            ('a', {'href': re.compile(r'tutorial|notebook|\.ipynb', re.I)}),
            # Pattern 2: 카드 형식
            ('div', {'class': re.compile(r'tutorial|card|item', re.I)}),
            # Pattern 3: 리스트 아이템
            ('li', {'class': re.compile(r'tutorial|resource', re.I)}),
        ]
        
        for tag, attrs in patterns:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                # 링크 추출
                link = None
                if tag == 'a':
                    link = elem.get('href')
                else:
                    link_elem = elem.find('a')
                    if link_elem:
                        link = link_elem.get('href')
                
                if not link:
                    continue
                    
                # 절대 URL로 변환
                if not link.startswith('http'):
                    link = f"https://marine.copernicus.eu{link}"
                
                # 제목 추출
                title = elem.get_text(strip=True)[:100] if elem.get_text() else f"Tutorial_{tutorial_id}"
                title = self.sanitize_filename(title)
                
                # 중복 체크
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
        
    def sanitize_filename(self, filename: str) -> str:
        """
        파일명으로 사용할 수 없는 문자 제거
        
        Parameters:
            filename: 원본 파일명
            
        Returns:
            정제된 파일명
        """
        # 특수문자 제거
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 공백을 언더스코어로 변경
        filename = filename.replace(' ', '_')
        # 연속된 언더스코어 제거
        filename = re.sub(r'_+', '_', filename)
        # 앞뒤 언더스코어 제거
        filename = filename.strip('_')
        # 최대 길이 제한
        return filename[:50] if len(filename) > 50 else filename
        
    def extract_resources(self, tutorial_url: str) -> List[Dict]:
        """
        튜토리얼 페이지에서 다운로드 가능한 리소스 추출
        
        Parameters:
            tutorial_url: 튜토리얼 페이지 URL
            
        Returns:
            리소스 정보 리스트
        """
        resources = []
        content = self.get_page_content(tutorial_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        # 다운로드 가능한 파일 패턴
        file_patterns = [
            r'\.ipynb',  # Jupyter notebooks
            r'\.nc',     # NetCDF files
            r'\.csv',    # CSV files
            r'\.json',   # JSON files
            r'\.py',     # Python scripts
            r'\.zip',    # Zip archives
            r'\.tar',    # Tar archives
            r'\.pdf',    # PDF documents
        ]
        
        pattern = '|'.join(file_patterns)
        links = soup.find_all('a', href=re.compile(pattern, re.I))
        
        for link in links:
            href = link.get('href')
            if not href:
                continue
                
            # 절대 URL로 변환
            if not href.startswith('http'):
                if href.startswith('/'):
                    href = f"https://marine.copernicus.eu{href}"
                else:
                    href = f"{tutorial_url}/{href}"
                    
            # 파일명 추출
            filename = href.split('/')[-1].split('?')[0]
            if not filename:
                filename = 'unknown_file'
                
            resources.append({
                'url': href,
                'filename': filename,
                'type': filename.split('.')[-1] if '.' in filename else 'unknown'
            })
            
        return resources
        
    def download_file(self, url: str, filepath: Path, retry: int = 3) -> bool:
        """
        파일 다운로드
        
        Parameters:
            url: 다운로드 URL
            filepath: 저장할 파일 경로
            retry: 재시도 횟수
            
        Returns:
            성공 여부
        """
        for attempt in range(retry):
            try:
                response = self.session.get(url, stream=True, timeout=60)
                response.raise_for_status()
                
                # 파일 크기 확인
                total_size = int(response.headers.get('content-length', 0))
                
                # 다운로드
                with open(filepath, 'wb') as f:
                    if total_size == 0:
                        f.write(response.content)
                    else:
                        with tqdm(total=total_size, unit='B', unit_scale=True, desc=filepath.name) as pbar:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    pbar.update(len(chunk))
                                    
                return True
                
            except Exception as e:
                if attempt == retry - 1:
                    print(f"다운로드 실패: {filepath.name} - {str(e)}")
                    return False
                time.sleep(2 ** attempt)  # 지수 백오프
                
        return False
        
    def process_tutorial(self, tutorial: Dict) -> Dict:
        """
        개별 튜토리얼 처리
        
        Parameters:
            tutorial: 튜토리얼 정보
            
        Returns:
            처리 결과
        """
        print(f"\n처리 중: {tutorial['title']}")
        
        # 튜토리얼 폴더 생성
        tutorial_dir = self.output_dir / tutorial['folder']
        tutorial_dir.mkdir(exist_ok=True)
        
        # 리소스 추출
        resources = self.extract_resources(tutorial['url'])
        print(f"  발견된 리소스: {len(resources)}개")
        
        # 다운로드 결과
        result = {
            'tutorial': tutorial,
            'resources': [],
            'success': 0,
            'failed': 0
        }
        
        # 리소스 다운로드
        for resource in resources:
            filepath = tutorial_dir / resource['filename']
            
            # 이미 존재하는 파일 스킵
            if filepath.exists():
                print(f"  스킵 (이미 존재): {resource['filename']}")
                result['success'] += 1
                continue
                
            # 다운로드
            if self.download_file(resource['url'], filepath):
                result['success'] += 1
                resource['downloaded'] = True
                resource['path'] = str(filepath)
            else:
                result['failed'] += 1
                resource['downloaded'] = False
                
            result['resources'].append(resource)
            
        return result
        
    def save_metadata(self):
        """메타데이터 저장"""
        metadata_file = self.output_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scrape_date': datetime.now().isoformat(),
                'base_url': self.base_url,
                'tutorials': self.metadata
            }, f, indent=2, ensure_ascii=False)
            
        print(f"\n메타데이터 저장: {metadata_file}")
        
    def run(self):
        """스크래핑 실행"""
        print("="*50)
        print("코페르니쿠스 튜토리얼 스크래퍼 시작")
        print("="*50)
        
        try:
            # 튜토리얼 링크 추출
            tutorials = self.extract_tutorial_links()
            
            if not tutorials:
                print("튜토리얼을 찾을 수 없습니다.")
                return
                
            # 각 튜토리얼 처리
            for tutorial in tqdm(tutorials, desc="전체 진행"):
                result = self.process_tutorial(tutorial)
                self.metadata.append(result)
                
            # 메타데이터 저장
            self.save_metadata()
            
            # 결과 요약
            total_success = sum(m['success'] for m in self.metadata)
            total_failed = sum(m['failed'] for m in self.metadata)
            
            print("\n" + "="*50)
            print("스크래핑 완료!")
            print(f"처리된 튜토리얼: {len(tutorials)}개")
            print(f"다운로드 성공: {total_success}개")
            print(f"다운로드 실패: {total_failed}개")
            print("="*50)
            
        finally:
            self.close_selenium()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='코페르니쿠스 튜토리얼 스크래퍼')
    parser.add_argument(
        '--url',
        type=str,
        help='튜토리얼 페이지 URL',
        default="https://marine.copernicus.eu/services/user-learning-services/tutorials"
    )
    parser.add_argument(
        '--output',
        type=str,
        help='출력 디렉토리',
        default='tutorials'
    )
    
    args = parser.parse_args()
    
    # 스크래퍼 실행
    scraper = CopernicusScraper(base_url=args.url, output_dir=args.output)
    scraper.run()


if __name__ == "__main__":
    main()