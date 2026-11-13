"""모든 영화관 수집기가 지켜야 하는 공통 규칙."""

from abc import ABC, abstractmethod
from datetime import date

from core.models import Showtime


class ShowtimeSource(ABC):
    """영화관 1곳의 상영시간표를 가져오는 수집기.

    새 영화관을 추가하려면 이 클래스를 상속해서
    `chain` 과 `fetch_showtimes` 두 가지만 채우면 된다.
    """

    chain: str = ""
    # 실제 데이터인지(True), 샘플 데이터인지(False) 화면에 표시하기 위한 값
    is_live: bool = False

    @abstractmethod
    def fetch_showtimes(self, target_date: date, region: str) -> list[Showtime]:
        """해당 날짜, 지역의 상영 회차 목록을 공통 형식으로 돌려준다."""
