"""메가박스 상영시간표 수집기.

1. 전체극장 페이지(/theater/list)에서 지역별 극장 목록을 읽는다.
2. 극장마다 시간표를 요청한다 (홈페이지 '극장별 상영시간표' 화면과 같은 요청).
"""

import html
import re
from datetime import date

from core.models import MEGABOX, Showtime
from sources.base import PoliteSession, ShowtimeSource, parse_play_time

BASE_URL = "https://www.megabox.co.kr"
THEATER_LIST_URL = f"{BASE_URL}/theater/list"
SCHEDULE_URL = f"{BASE_URL}/on/oh/ohc/Brch/schedulePage.do"

# 메가박스 상영관 종류 코드 -> 화면 표시 이름
SCREEN_TYPES = {
    "NOR": "일반",
    "RCL": "일반",  # 르 리클라이너 (좌석만 다른 일반관)
    "CFT": "일반",  # 컴포트 (좌석만 다른 일반관)
    "DBC": "Dolby Cinema",
    "DVA": "Dolby Vision+Atmos",
    "MX4D": "MX4D",
    "TBS": "부티크 스위트",
    "TBQ": "더 부티크",
    "LUMINEON": "LED",
}


class MegaboxSource(ShowtimeSource):
    chain = MEGABOX
    is_live = True

    def __init__(self, http: PoliteSession | None = None):
        self.http = http or PoliteSession()

    def fetch_showtimes(self, target_date: date, region: str) -> list[Showtime]:
        theaters = parse_theater_list(self.http.request("GET", THEATER_LIST_URL).text)
        showtimes = []
        for brch_no, _name in theaters.get(region, []):
            response = self.http.request(
                "POST",
                SCHEDULE_URL,
                json={
                    "masterType": "brch",
                    "detailType": "area",
                    "brchNo": brch_no,
                    "brchNo1": brch_no,
                    "firstAt": "N",
                    "crtDe": date.today().strftime("%Y%m%d"),
                    "playDe": target_date.strftime("%Y%m%d"),
                },
            )
            showtimes += parse_schedule(response.json(), target_date, region)
        return showtimes


def parse_theater_list(page_html: str) -> dict[str, list[tuple[str, str]]]:
    """전체극장 페이지 -> {지역: [(극장번호, 극장이름), ...]}. 휴관 극장은 뺀다."""
    theaters = {}
    # 지역 버튼(<button class="sel-city">서울</button>) 기준으로 나눈다
    parts = re.split(r'<button type="button" class="sel-city">\s*([^<\s]+)', page_html)
    for region, block in zip(parts[1::2], parts[2::2]):
        found = re.findall(r'data-brch-no="(\d+)".*?title="[^"]*">([^<]+)</a>', block, re.S)
        theaters[region] = [
            (no, html.unescape(name).strip()) for no, name in found if "휴관" not in html.unescape(name)
        ]
    return theaters


def parse_schedule(data: dict, target_date: date, region: str) -> list[Showtime]:
    items = (data.get("megaMap") or {}).get("movieFormList") or []
    result = []
    for item in items:
        if item.get("playDe") and item["playDe"] != target_date.strftime("%Y%m%d"):
            continue
        result.append(
            Showtime(
                chain=MEGABOX,
                theater=item["brchNm"],
                region=region,
                # rpstMovieNm 은 '[굿즈패키지]' 같은 꼬리표가 없는 대표 제목
                movie_title=html.unescape(item.get("rpstMovieNm") or item["movieNm"]),
                start=parse_play_time(target_date, item["playStartTime"]),
                end=parse_play_time(target_date, item["playEndTime"]),
                screen_type=SCREEN_TYPES.get(item.get("theabKindCd"), item.get("theabKindCd") or "일반"),
                seats_left=int(item.get("restSeatCnt") or 0),
                total_seats=int(item.get("theabSeatCnt") or 0),
                booking_url=f"{BASE_URL}/theater/time?brchNo={item['brchNo']}",
                screen_name=html.unescape(item.get("theabExpoNm") or ""),
                bookable=item.get("bokdAbleAt", "Y") == "Y",
            )
        )
    return result
