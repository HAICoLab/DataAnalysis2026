"""뼈대 단계용 가짜(샘플) 데이터.

실제 크롤링을 붙이기 전에도 화면 전체가 동작하는지 확인하기 위해 사용한다.
같은 날짜를 넣으면 항상 같은 결과가 나오도록 만들었다 (테스트하기 쉽게).
"""

import random
from datetime import date, datetime, time, timedelta

from core.models import BoxOfficeEntry, Showtime, CGV, LOTTE, MEGABOX

# 샘플 영화: (제목, 상영 시간(분))
SAMPLE_MOVIES = [
    ("[샘플] 우주 탐험대", 148),
    ("[샘플] 한밤의 추리극", 121),
    ("[샘플] 바다의 노래", 105),
    ("[샘플] 마지막 경기", 132),
    ("[샘플] 고양이 탐정", 98),
]

# 영화사별 샘플 극장 (서울)
SAMPLE_THEATERS = {
    CGV: ["용산아이파크몰", "강남", "영등포"],
    LOTTE: ["월드타워", "건대입구", "홍대입구"],
    MEGABOX: ["코엑스", "성수", "신촌"],
}

# 영화사별 예매 페이지 (지금은 홈페이지로 연결)
BOOKING_URLS = {
    CGV: "https://www.cgv.co.kr",
    LOTTE: "https://www.lottecinema.co.kr",
    MEGABOX: "https://www.megabox.co.kr",
}

# 영화사별 특별관 이름
SPECIAL_SCREENS = {
    CGV: ["IMAX", "4DX", "SCREENX"],
    LOTTE: ["SUPER PLEX", "SUPER 4D", "샤롯데"],
    MEGABOX: ["Dolby Cinema", "MX4D", "더 부티크"],
}


def sample_showtimes(chain: str, target_date: date, region: str) -> list[Showtime]:
    rng = random.Random(f"{chain}-{target_date.isoformat()}")
    result = []
    for theater in SAMPLE_THEATERS[chain]:
        for title, runtime in rng.sample(SAMPLE_MOVIES, k=3):
            screen_type = rng.choice(["일반", "일반", "일반", *SPECIAL_SCREENS[chain]])
            total = rng.choice([120, 180, 250, 300])
            start = datetime.combine(target_date, time(9, 0)) + timedelta(minutes=rng.randint(0, 60))
            while start.hour < 23:
                result.append(
                    Showtime(
                        chain=chain,
                        theater=theater,
                        region=region,
                        movie_title=title,
                        start=start,
                        end=start + timedelta(minutes=runtime),
                        screen_type=screen_type,
                        seats_left=rng.randint(0, total),
                        total_seats=total,
                        booking_url=BOOKING_URLS[chain],
                    )
                )
                # 상영 시간 + 청소 시간(15~30분) 뒤에 다음 회차
                start += timedelta(minutes=runtime + rng.choice([15, 20, 30]))
    return result


def sample_box_office(target_date: date) -> list[BoxOfficeEntry]:
    rng = random.Random(f"boxoffice-{target_date.isoformat()}")
    entries = []
    daily = 120_000
    for rank, (title, _) in enumerate(SAMPLE_MOVIES, start=1):
        daily = int(daily * rng.uniform(0.4, 0.8))
        entries.append(
            BoxOfficeEntry(
                rank=rank,
                movie_title=title,
                daily_audience=daily,
                total_audience=daily * rng.randint(5, 40),
                open_date=target_date - timedelta(days=rng.randint(1, 30)),
            )
        )
    return entries
