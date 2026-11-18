"""모든 영화관 수집기가 지켜야 하는 공통 규칙과 공용 도구."""

import time
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta

import requests

from core.models import Showtime

# 영화관 서버에 부담을 주지 않도록 요청 사이에 쉬는 시간(초)
REQUEST_DELAY = 0.3
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130 Safari/537.36"
)


class ShowtimeSource(ABC):
    """영화관 1곳의 상영시간표를 가져오는 수집기.

    새 영화관을 추가하려면 이 클래스를 상속해서
    `chain` 과 `fetch_showtimes` 두 가지만 채우면 된다.
    """

    chain: str = ""
    # 실제 데이터인지(True), 아닌지(False) 화면에 표시하기 위한 값
    is_live: bool = False
    # 화면에 띄울 안내 문구 (예: 자동 조회가 막혀 있는 경우)
    notice: str = ""

    @abstractmethod
    def fetch_showtimes(self, target_date: date, region: str) -> list[Showtime]:
        """해당 날짜, 지역의 상영 회차 목록을 공통 형식으로 돌려준다."""


class PoliteSession:
    """요청마다 잠깐 쉬어 가는 HTTP 세션."""

    def __init__(self, delay: float = REQUEST_DELAY):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last_request = 0.0

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            response = self.session.request(method, url, timeout=15, **kwargs)
        finally:
            self._last_request = time.monotonic()
        response.raise_for_status()
        return response


def parse_play_time(play_date: date, hhmm: str) -> datetime:
    """'19:30' 같은 시각을 datetime 으로 바꾼다.

    심야 회차는 '24:32', '25:10' 처럼 24시를 넘겨 표기되므로 다음 날로 넘긴다.
    """
    hour, minute = (int(x) for x in hhmm.strip().split(":"))
    return datetime.combine(play_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
