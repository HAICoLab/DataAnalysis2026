"""롯데시네마 상영시간표 수집기.

1. 'GetTicketingPageTOBE' 요청으로 지역별 극장 목록을 받는다.
2. 극장마다 'GetPlaySequence' 요청으로 시간표를 받는다.
(둘 다 홈페이지 예매 화면이 사용하는 요청과 같다)
"""

import json
from datetime import date

from core.models import LOTTE, Showtime
from sources.base import PoliteSession, ShowtimeSource, parse_play_time

BASE_URL = "https://www.lottecinema.co.kr"
DATA_URL = f"{BASE_URL}/LCWS/Ticketing/TicketingData.aspx"
COMMON_PARAMS = {"channelType": "HO", "osType": "W", "osVersion": "Chrome"}
# 좌석만 다른 일반관은 '일반'으로 취급 (특별관 필터에서 빠지도록)
GENERAL_SCREENS = {"일반", "리클라이너"}


class LotteSource(ShowtimeSource):
    chain = LOTTE
    is_live = True

    def __init__(self, http: PoliteSession | None = None):
        self.http = http or PoliteSession()

    def _call(self, method_name: str, **params) -> dict:
        param_list = json.dumps({"MethodName": method_name, **COMMON_PARAMS, **params})
        # 롯데시네마는 요청을 'paramList' 라는 이름의 form 값으로 받는다
        response = self.http.request("POST", DATA_URL, files={"paramList": (None, param_list)})
        return response.json()

    def fetch_showtimes(self, target_date: date, region: str) -> list[Showtime]:
        cinemas = parse_cinema_list(self._call("GetTicketingPageTOBE", memberOnNo="0"))
        showtimes = []
        for cinema_param, _name in cinemas.get(region, []):
            data = self._call(
                "GetPlaySequence",
                playDate=target_date.isoformat(),
                cinemaID=cinema_param,
                representationMovieCode="",
            )
            showtimes += parse_play_sequence(data, target_date, region, cinema_param)
        return showtimes


def parse_cinema_list(data: dict) -> dict[str, list[tuple[str, str]]]:
    """극장 목록 응답 -> {지역: [('1|0001|1016', '월드타워'), ...]}."""
    areas = {
        a["DetailDivisionCode"]: a["GroupNameKR"]
        for a in data["CinemaDivison"]["AreaDivisions"]["Items"]
        if a["DivisionCode"] == 1  # 1 = 지역별 구분 (2 = 스페셜관별 구분)
    }
    cinemas = {}
    for c in data["Cinemas"]["Cinemas"]["Items"]:
        region = areas.get(c["DetailDivisionCode"])
        if c["DivisionCode"] != 1 or region is None:
            continue
        param = f"{c['DivisionCode']}|{c['DetailDivisionCode']}|{c['CinemaID']}"
        cinemas.setdefault(region, []).append((param, c["CinemaNameKR"]))
    return cinemas


def parse_play_sequence(data: dict, target_date: date, region: str, cinema_param: str) -> list[Showtime]:
    division, detail_division, cinema_id = cinema_param.split("|")
    booking_url = (
        f"{BASE_URL}/NLCHS/Cinema/Detail?divisionCode={division}"
        f"&detailDivisionCode={detail_division}&cinemaID={cinema_id}"
    )
    items = (data.get("PlaySeqs") or {}).get("Items") or []
    result = []
    for item in items:
        if not item.get("StartTime") or not item.get("EndTime"):
            continue
        result.append(
            Showtime(
                chain=LOTTE,
                theater=item["CinemaNameKR"],
                region=region,
                movie_title=item["MovieNameKR"],
                start=parse_play_time(target_date, item["StartTime"]),
                end=parse_play_time(target_date, item["EndTime"]),
                screen_type=_screen_type(item.get("ScreenDivisionNameKR")),
                seats_left=int(item.get("BookingSeatCount") or 0),  # 예매 가능한(남은) 좌석
                total_seats=int(item.get("TotalSeatCount") or 0),
                booking_url=booking_url,
                screen_name=item.get("ScreenNameKR") or "",
                bookable=item.get("IsBookingYN", "Y") == "Y",
            )
        )
    return result


def _screen_type(name: str | None) -> str:
    return "일반" if not name or name in GENERAL_SCREENS else name
