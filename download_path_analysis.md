# Copernicus Marine 다운로드 경로 분석

## 다운로드 가능한 링크들 (발견된 5개)

### 1. Arctic Ocean Training - Copernicus 소개 (초급)
- **Copernicus 페이지**: `/arctic-ocean-training-2022-discover-copernicus-marine-service`
- **Mercator Ocean 링크**: `https://atlas.mercator-ocean.fr/s/ZqtwdLNzoQH55JE/download`
- **파일**: Beginner_overview.zip (70MB+)
- **상태**: ✅ 다운로드 확인됨

### 2. Arctic Ocean Training - 열염순환
- **Copernicus 페이지**: `/arctic-ocean-training-2022-thermohaline-circulation`
- **Mercator Ocean 링크**: `https://atlas.mercator-ocean.fr/s/WCM44bp3bFc63PB/download`
- **상태**: 다운로드 가능 (테스트 필요)

### 3. MarineData4Africa - 앙골라 벵겔라 시스템
- **Copernicus 페이지**: `/marinedata4africa-training-2023-angola-benguela-system-intermediate`
- **Mercator Ocean 링크**: `https://atlas.mercator-ocean.fr/s/Cf8imxcnmYaAZYL/download`
- **상태**: 다운로드 가능 (테스트 필요)

### 4. Baltic Sea Training - 부영양화
- **Copernicus 페이지**: `/baltic-sea-training-2022-eutrophication`
- **Mercator Ocean 링크**: `https://atlas.mercator-ocean.fr/s/oM2SaXder35GbwW/download`
- **상태**: 다운로드 가능 (테스트 필요)

## 다운로드 경로 찾는 방법

### 1단계: Copernicus 튜토리얼 메인 페이지
```
https://marine.copernicus.eu/services/user-learning-services/tutorials
```
- 여러 튜토리얼 카드들이 나열됨
- 각 카드를 클릭하면 개별 튜토리얼 페이지로 이동

### 2단계: 개별 튜토리얼 페이지
```
예: /arctic-ocean-training-2022-discover-copernicus-marine-service
```
- 튜토리얼 설명과 함께 "Access" 또는 "Download" 버튼 존재
- 이 버튼들이 Mercator Ocean 공유 링크로 연결됨

### 3단계: Mercator Ocean 공유 페이지
```
예: https://atlas.mercator-ocean.fr/s/ZqtwdLNzoQH55JE
```
- 실제 파일이 호스팅되는 곳
- `/download`를 URL 끝에 추가하면 직접 다운로드 가능

## 자동화된 크롤링 프로세스

```python
# multilevel_scraper.py가 하는 일:

1. Copernicus 메인 페이지 방문
   ↓
2. 튜토리얼 링크들 수집 (tutorial, training 키워드)
   ↓
3. 각 튜토리얼 페이지 방문
   ↓
4. Download/Access 버튼 찾기
   ↓
5. Mercator Ocean 링크 추출
   ↓
6. /download 추가하여 직접 다운로드 URL 생성
```

## 다운로드 가능 여부 판단 기준

1. **Mercator Ocean 링크**: `atlas.mercator-ocean.fr/s/[ID]` 형태
2. **직접 다운로드**: URL 끝에 `/download` 추가
3. **파일 형식**: 대부분 ZIP 파일 (교육 자료, 노트북, 데이터 포함)

## 추가 가능한 소스들

현재 스크래퍼가 놓칠 수 있는 것들:
- GitHub 링크 (일부 튜토리얼이 GitHub에 호스팅)
- Zenodo 링크 (학술 데이터)
- Google Drive 링크 (일부 워크샵 자료)
- 직접 .ipynb 파일 링크

## 테스트 명령어

특정 링크 다운로드 확인:
```bash
# curl로 헤더 확인
curl -I -L "https://atlas.mercator-ocean.fr/s/[ID]/download"

# 실제 다운로드
curl -L "https://atlas.mercator-ocean.fr/s/[ID]/download" -o "filename.zip"
```

## 현재 성과

- **발견된 다운로드 링크**: 5개
- **확인된 다운로드**: 1개 (70MB ZIP)
- **예상 총 크기**: 200-500MB (모든 튜토리얼 포함 시)