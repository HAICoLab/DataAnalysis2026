"""CGV 상영시간표 수집기.

TODO(4단계): 샘플 데이터 대신 CGV 홈페이지에서 실제 시간표를 가져오기.
"""

from datetime import date

from core.models import CGV, Showtime
from sources.base import ShowtimeSource
from sources.sample_data import sample_showtimes


class CgvSource(ShowtimeSource):
    chain = CGV
    is_live = False

    def fetch_showtimes(self, target_date: date, region: str) -> list[Showtime]:
        return sample_showtimes(self.chain, target_date, region)
