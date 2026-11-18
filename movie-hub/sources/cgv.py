"""CGV 상영시간표 수집기.

CGV 홈페이지는 프로그램(브라우저가 아닌 접속)을 감지하면
"비정상적으로 접속한 것이 확인되어 이용이 제한되었어요" 화면(403)을 보여주며 차단한다.
차단을 우회하지 않고, 화면에 안내와 홈페이지 링크만 보여준다.
"""

from datetime import date

from core.models import CGV, Showtime
from sources.base import ShowtimeSource

CGV_URL = "https://www.cgv.co.kr"


class CgvSource(ShowtimeSource):
    chain = CGV
    is_live = False
    notice = f"CGV는 홈페이지에서 자동 조회를 차단하고 있어 시간표를 가져올 수 없습니다. [CGV 홈페이지에서 확인하기]({CGV_URL})"

    def fetch_showtimes(self, target_date: date, region: str) -> list[Showtime]:
        return []
