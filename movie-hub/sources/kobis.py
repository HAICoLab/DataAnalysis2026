"""영화진흥위원회(KOBIS) 박스오피스.

.env 파일에 KOBIS_API_KEY 가 있으면 실제 데이터를, 없으면 샘플 데이터를 돌려준다.
API 키 발급: https://www.kobis.or.kr/kobisopenapi/ (회원가입 후 '키 발급')
"""

import os
from datetime import date, datetime

import requests

from core.models import BoxOfficeEntry
from sources.sample_data import sample_box_office

DAILY_BOX_OFFICE_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
)


def has_api_key() -> bool:
    return bool(os.getenv("KOBIS_API_KEY"))


def fetch_daily_box_office(target_date: date) -> list[BoxOfficeEntry]:
    """해당 날짜의 일별 박스오피스 TOP 10.

    참고: KOBIS 일별 박스오피스는 '어제'까지만 집계되어 있다.
    """
    api_key = os.getenv("KOBIS_API_KEY")
    if not api_key:
        return sample_box_office(target_date)

    response = requests.get(
        DAILY_BOX_OFFICE_URL,
        params={"key": api_key, "targetDt": target_date.strftime("%Y%m%d")},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if "faultInfo" in data:
        raise RuntimeError(f"KOBIS 오류: {data['faultInfo'].get('message')}")

    return [
        BoxOfficeEntry(
            rank=int(item["rank"]),
            movie_title=item["movieNm"],
            daily_audience=int(item["audiCnt"]),
            total_audience=int(item["audiAcc"]),
            open_date=_parse_date(item.get("openDt")),
        )
        for item in data["boxOfficeResult"]["dailyBoxOfficeList"]
    ]


def _parse_date(text: str | None) -> date | None:
    if not text or not text.strip():
        return None
    return datetime.strptime(text.strip(), "%Y-%m-%d").date()
