"""3사 결과를 한데 모으고, 걸러내고, 정렬하는 곳."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime

from core.models import Showtime
from core.theaters import district_of
from sources.base import ShowtimeSource
from sources.cgv import CgvSource
from sources.lotte import LotteSource
from sources.megabox import MegaboxSource

GENERAL_SCREEN = "일반"


def default_sources() -> list[ShowtimeSource]:
    return [CgvSource(), LotteSource(), MegaboxSource()]


@dataclass
class CollectResult:
    showtimes: list[Showtime] = field(default_factory=list)
    # 영화사 -> 오류 메시지 (한 곳이 실패해도 나머지는 보여주기 위해 따로 모아둔다)
    errors: dict[str, str] = field(default_factory=dict)


def collect_showtimes(
    sources: list[ShowtimeSource], target_date: date, region: str
) -> CollectResult:
    """영화관들을 동시에 조회한다 (영화관 안에서는 극장을 하나씩 천천히 조회)."""
    result = CollectResult()
    with ThreadPoolExecutor(max_workers=max(len(sources), 1)) as pool:
        futures = [(s, pool.submit(s.fetch_showtimes, target_date, region)) for s in sources]
        for source, future in futures:
            try:
                result.showtimes.extend(future.result())
            except Exception as e:  # 한 영화관이 고장 나도 전체가 멈추지 않도록
                result.errors[source.chain] = str(e)
    return result


def filter_showtimes(
    showtimes: list[Showtime],
    chains: list[str] | None = None,
    movie_title: str | None = None,
    special_only: bool = False,
    hide_past: datetime | None = None,
    bookable_only: bool = False,
    start_between: tuple[datetime, datetime] | None = None,
    districts: list[str] | None = None,
) -> list[Showtime]:
    """조건에 맞는 회차만 남긴다. 값이 None/False 인 조건은 적용하지 않는다.

    bookable_only: 영화관이 '예매 가능'으로 표시했고 남은 좌석이 있는 회차만
    start_between: 시작 시각이 (이상, 미만) 범위 안인 회차만
    """
    return [
        s
        for s in showtimes
        if (chains is None or s.chain in chains)
        and (movie_title is None or s.movie_title == movie_title)
        and (not special_only or s.screen_type != GENERAL_SCREEN)
        and (hide_past is None or s.start >= hide_past)
        and (not bookable_only or (s.bookable and s.seats_left > 0))
        and (start_between is None or start_between[0] <= s.start < start_between[1])
        and (districts is None or district_of(s.chain, s.theater) in districts)
    ]


def sort_showtimes(showtimes: list[Showtime], by: str = "time") -> list[Showtime]:
    """by: 'time'(시작 시간순) 또는 'seats'(남은 좌석 많은 순)."""
    if by == "seats":
        return sorted(showtimes, key=lambda s: (-s.seats_left, s.start))
    return sorted(showtimes, key=lambda s: (s.start, s.chain, s.theater))


def movie_titles(showtimes: list[Showtime]) -> list[str]:
    return sorted({s.movie_title for s in showtimes})


def theater_label(s: Showtime) -> str:
    return f"{s.chain} {s.theater}"


def district_list(showtimes: list[Showtime]) -> list[str]:
    return sorted({district_of(s.chain, s.theater) for s in showtimes})


def count_by_theater_and_hour(
    showtimes: list[Showtime], target_date: date
) -> dict[tuple[str, str], dict[int, int]]:
    """{(구, 극장): {시(hour): 회차 수}}. 자정 넘긴 회차는 24, 25... 시로 센다."""
    midnight = datetime.combine(target_date, datetime.min.time())
    counts: dict[tuple[str, str], dict[int, int]] = {}
    for s in showtimes:
        key = (district_of(s.chain, s.theater), theater_label(s))
        hour = int((s.start - midnight).total_seconds() // 3600)
        counts.setdefault(key, {})
        counts[key][hour] = counts[key].get(hour, 0) + 1
    return dict(sorted(counts.items()))


def group_by_district(showtimes: list[Showtime]) -> dict[str, dict[str, list[Showtime]]]:
    """{구: {극장: [회차, ...]}}. 회차가 많은 구부터, 구 안에서는 극장 이름순."""
    groups: dict[str, dict[str, list[Showtime]]] = {}
    for s in sorted(showtimes, key=lambda s: s.start):
        groups.setdefault(district_of(s.chain, s.theater), {}).setdefault(theater_label(s), []).append(s)
    return {
        d: dict(sorted(theaters.items()))
        for d, theaters in sorted(groups.items(), key=lambda kv: -sum(len(v) for v in kv[1].values()))
    }
