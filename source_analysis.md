# 소스 처리 방식 분석

## 📍 다루는 소스들

### 1. **GitHub (주요 소스)**
```python
# GitHub API 엔드포인트들
- /repos/{owner}/{repo}/contents  # 저장소 내용
- /search/code                     # 코드 검색
- raw.githubusercontent.com        # 실제 파일 다운로드
```

**처리 방식:**
- API로 저장소 탐색 → JSON 응답 파싱
- HTML URL을 Raw URL로 변환
- 예: `github.com/.../blob/main/file.ipynb` → `raw.githubusercontent.com/.../main/file.ipynb`

### 2. **Zenodo (학술 데이터)**
```python
# Zenodo API
- https://zenodo.org/api/records
- 검색어: "copernicus marine"
```

**처리 방식:**
- REST API로 데이터셋 검색
- 메타데이터에서 파일 URL 추출
- 직접 다운로드 링크 제공

### 3. **Copernicus Marine 웹사이트**
```python
# 스캔하는 페이지들
- /services/user-learning-services/tutorials
- /services/use-cases
- help.marine.copernicus.eu
```

**처리 방식:**
- HTML 페이지 GET 요청
- BeautifulSoup으로 파싱
- `<a>` 태그에서 href 추출

## 🔄 소스별 처리 과정

### GitHub 처리 과정:
```python
1. API 호출 → 2. JSON 파싱 → 3. URL 변환 → 4. 다운로드
```

### Zenodo 처리 과정:
```python
1. 검색 API → 2. 결과 필터링 → 3. 다운로드 URL 획득 → 4. 직접 다운로드
```

### 웹페이지 처리 과정:
```python
1. HTTP GET → 2. HTML 파싱 → 3. 링크 추출 → 4. 필터링 → 5. 다운로드
```

## 📊 소스 우선순위와 신뢰도

| 소스 | 우선순위 | 신뢰도 | 장점 | 단점 |
|------|---------|--------|------|------|
| GitHub API | 1순위 | 높음 | 구조화된 데이터, 빠른 속도 | API 제한 (60회/시간) |
| Zenodo | 2순위 | 높음 | 학술 검증 데이터 | Copernicus 전용 아님 |
| 웹 크롤링 | 3순위 | 보통 | 최신 정보 | JavaScript 렌더링 필요 |

## 🛠️ 소스 처리 기술

### 1. **세션 관리**
```python
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0...'  # 브라우저로 위장
})
```

### 2. **URL 변환 로직**
```python
def convert_to_raw_url(github_url):
    # GitHub 뷰어 URL → 다운로드 가능 URL
    raw_url = github_url.replace('github.com', 'raw.githubusercontent.com')
    raw_url = raw_url.replace('/blob/', '/')
    return raw_url
```

### 3. **재귀 탐색**
```python
def _search_github_files(self, api_url, resources, depth=0, max_depth=2):
    if depth > max_depth:
        return
    # 디렉토리 내부 재귀 탐색
```

### 4. **필터링 기준**
```python
# 파일 확장자 필터
if filename.endswith(('.ipynb', '.zip', '.nc')):
    # 다운로드 대상

# 키워드 필터
relevant_keywords = ['tutorial', 'notebook', 'copernicus', 'marine']
```

## 📈 소스별 성공률

현재 테스트 결과:
- **GitHub**: 4/6 저장소 (66.7%)
- **Zenodo**: 3/3 검색 (100%)
- **웹사이트**: 3/3 페이지 (100%)

## 🔐 보안 고려사항

1. **타임아웃 설정**: 30초로 제한
2. **파일 크기 제한**: 10MB 기본값
3. **확장자 검증**: 허용된 확장자만
4. **중복 다운로드 방지**: 파일 존재 확인
5. **에러 처리**: try-except로 안전하게 처리

## 💡 개선 가능한 부분

1. **인증 토큰 사용**: GitHub API 제한 확장
2. **비동기 처리**: 더 빠른 다운로드
3. **프록시 지원**: 접근 제한 우회
4. **더 많은 소스**: GitLab, Bitbucket 등
5. **스마트 캐싱**: 메타데이터 캐싱