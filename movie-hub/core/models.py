"""모든 영화관 데이터가 맞춰야 하는 '공통 형식'.

CGV, 롯데시네마, 메가박스는 각자 다른 모양으로 정보를 주지만,
수집기(sources/)는 반드시 아래 모양으로 바꿔서 넘겨줘야 한다.
"""

from dataclasses import dataclass
from datetime import date, datetime


# 영화사 이름 (화면 표시와 필터에 공통으로 사용)
CGV = "CGV"
LOTTE = "롯데시네마"
MEGABOX = "메가박스"
ALL_CHAINS = [CGV, LOTTE, MEGABOX]


@dataclass(frozen=True)
class Showtime:
    """상영 회차 1개 (시간표의 한 줄)."""

    chain: str            # 영화사: CGV / 롯데시네마 / 메가박스
    theater: str          # 극장: 용산아이파크몰
    region: str           # 지역: 서울
    movie_title: str      # 영화 제목
    start: datetime       # 시작 시각
    end: datetime         # 종료 시각
    screen_type: str      # 상영관 종류: 일반 / IMAX / 4DX ...
    seats_left: int       # 남은 좌석
    total_seats: int      # 전체 좌석
    booking_url: str      # 예매 페이지 주소


@dataclass(frozen=True)
class BoxOfficeEntry:
    """박스오피스 순위 1줄."""

    rank: int
    movie_title: str
    daily_audience: int     # 해당 날짜 관객 수
    total_audience: int     # 누적 관객 수
    open_date: date | None  # 개봉일
