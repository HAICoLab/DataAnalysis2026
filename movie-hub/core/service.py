"""3사 결과를 한데 모으고, 걸러내고, 정렬하는 곳."""

from dataclasses import dataclass, field
from datetime import date, datetime

from core.models import Showtime
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
    result = CollectResult()
    for source in sources:
        try:
            result.showtimes.extend(source.fetch_showtimes(target_date, region))
        except Exception as e:  # 한 영화관이 고장 나도 전체가 멈추지 않도록
            result.errors[source.chain] = str(e)
    return result


def filter_showtimes(
    showtimes: list[Showtime],
    chains: list[str] | None = None,
    movie_title: str | None = None,
    special_only: bool = False,
    hide_past: datetime | None = None,
    hide_sold_out: bool = False,
) -> list[Showtime]:
    """조건에 맞는 회차만 남긴다. 값이 None/False 인 조건은 적용하지 않는다."""
    return [
        s
        for s in showtimes
        if (chains is None or s.chain in chains)
        and (movie_title is None or s.movie_title == movie_title)
        and (not special_only or s.screen_type != GENERAL_SCREEN)
        and (hide_past is None or s.start >= hide_past)
        and (not hide_sold_out or s.seats_left > 0)
    ]


def sort_showtimes(showtimes: list[Showtime], by: str = "time") -> list[Showtime]:
    """by: 'time'(시작 시간순) 또는 'seats'(남은 좌석 많은 순)."""
    if by == "seats":
        return sorted(showtimes, key=lambda s: (-s.seats_left, s.start))
    return sorted(showtimes, key=lambda s: (s.start, s.chain, s.theater))


def movie_titles(showtimes: list[Showtime]) -> list[str]:
    return sorted({s.movie_title for s in showtimes})
