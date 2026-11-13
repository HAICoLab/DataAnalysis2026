# 🎬 영화관 통합 시간표 (movie-hub)

CGV · 롯데시네마 · 메가박스의 상영시간표를 **한 화면에서 비교**하는 프로그램입니다.
영화를 고르면 세 영화관의 회차를 시간순(또는 남은 좌석순)으로 모아 보여주고, 원하는 회차를 누르면 해당 영화관 예매 페이지로 이동합니다.

> ⚠️ **현재는 초기(뼈대) 버전입니다.**
> 상영시간표는 모두 **샘플(가짜) 데이터**이며, 영화 제목 앞에 `[샘플]`이 붙어 있습니다.
> 화면 왼쪽 아래 **"데이터 상태"**에서 🟡샘플 / 🟢실제 여부를 확인할 수 있습니다.

## 주요 기능

- 📊 박스오피스 TOP 10 (영화진흥위원회 KOBIS)
- 🕐 3사 상영시간표 통합 조회
- 🔍 필터: 날짜 · 영화관 · 영화 · 특별관(IMAX, 4DX, Dolby 등)만 보기 · 매진 숨기기
- ↕️ 정렬: 시간순 / 남은 좌석 많은 순
- 🎟️ 회차별 예매 링크

## 시작하기

### 1. 준비물
- [Miniconda](https://docs.anaconda.com/miniconda/) (또는 Anaconda)
- 이 저장소 내려받기
  ```bash
  git clone https://github.com/HAICoLab/DataAnalysis2026.git
  cd DataAnalysis2026/movie-hub
  ```

### 2. 설치 (처음 한 번만)
```bash
conda env create -f environment.yml
```
`movie-hub`라는 가상환경이 만들어지고 필요한 도구가 자동으로 설치됩니다.

### 3. 실행
```bash
conda activate movie-hub
streamlit run app.py
```
웹브라우저가 자동으로 열립니다. 열리지 않으면 http://localhost:8501 에 접속하세요.
종료는 터미널에서 `Ctrl + C`.

### 4. (선택) 실제 박스오피스 보기
1. [KOBIS 오픈API](https://www.kobis.or.kr/kobisopenapi/)에서 회원가입 후 **키 발급** (무료)
2. `.env.example` 파일을 복사해서 이름을 `.env`로 변경
3. `KOBIS_API_KEY=` 뒤에 발급받은 키를 붙여넣고 앱을 다시 실행

> `.env` 파일은 git에 올라가지 않습니다. API 키는 비밀번호처럼 다른 사람과 공유하지 마세요.

## 자동 점검 (테스트)
```bash
pytest
```

## 폴더 구조

```
movie-hub/
├── app.py              화면 (실행 시작점)
├── core/
│   ├── models.py       공통 형식 (시간표 한 줄의 모양)
│   └── service.py      3사 결과 합치기 · 필터 · 정렬
├── sources/            데이터를 가져오는 곳
│   ├── base.py         모든 수집기가 지켜야 할 공통 규칙
│   ├── cgv.py          CGV
│   ├── lotte.py        롯데시네마
│   ├── megabox.py      메가박스
│   ├── kobis.py        박스오피스 (KOBIS)
│   └── sample_data.py  샘플 데이터
└── tests/              자동 점검 코드
```

**동작 방식:** `sources/`의 수집기들이 각 영화관 데이터를 가져와 `core/models.py`의 **공통 형식**으로 바꿉니다 → `core/service.py`가 합치고 걸러서 → `app.py`가 화면에 보여줍니다.
한 영화관의 수집이 실패해도 나머지 영화관은 정상적으로 표시됩니다.

## 새 영화관 / 실제 데이터 연결하기

`sources/base.py`의 `ShowtimeSource`를 상속해 `fetch_showtimes()`만 구현하면 됩니다.
반환값은 반드시 `core/models.py`의 `Showtime` 목록이어야 하며, 실제 데이터를 연결했다면 `is_live = True`로 바꿔 주세요.

## 진행 계획

- [x] 1단계: 뼈대 (샘플 데이터로 화면 완성)
- [ ] 2단계: KOBIS 실제 박스오피스 연결
- [ ] 3단계: 메가박스 실제 시간표 연결
- [ ] 4단계: CGV · 롯데시네마 실제 시간표 연결
- [ ] 5단계: 위치 기반 정렬, 영화 제목 자동 매칭, 알림 등

## 이용 안내

- 이 프로젝트는 **학습 및 개인 용도**로 만들어졌습니다. **상업적으로 이용하지 마세요.**
- 각 영화관의 상영 정보와 상표의 권리는 해당 회사에 있습니다. 이 프로젝트는 CGV, 롯데시네마, 메가박스와 관련이 없습니다.
- 실제 데이터 수집 기능을 추가할 때는 각 사이트의 이용약관과 robots.txt를 확인하세요. 또한 **과도한 요청을 보내지 마세요** (기본으로 10분 캐싱이 적용되어 있습니다).
