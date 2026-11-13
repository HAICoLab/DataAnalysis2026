from datetime import date, datetime

from core import service
from core.models import CGV, MEGABOX
from sources.base import ShowtimeSource

TARGET = date(2026, 11, 13)


def test_all_three_chains_return_showtimes():
    result = service.collect_showtimes(service.default_sources(), TARGET, "서울")
    assert result.errors == {}
    assert {s.chain for s in result.showtimes} == {"CGV", "롯데시네마", "메가박스"}


def test_one_broken_source_does_not_stop_others():
    class BrokenSource(ShowtimeSource):
        chain = "고장난영화관"

        def fetch_showtimes(self, target_date, region):
            raise ConnectionError("접속 실패")

    sources = [BrokenSource(), *service.default_sources()]
    result = service.collect_showtimes(sources, TARGET, "서울")
    assert "고장난영화관" in result.errors
    assert len(result.showtimes) > 0


def test_filters():
    showtimes = service.collect_showtimes(service.default_sources(), TARGET, "서울").showtimes
    noon = datetime(2026, 11, 13, 12, 0)
    title = service.movie_titles(showtimes)[0]

    filtered = service.filter_showtimes(
        showtimes, chains=[CGV, MEGABOX], movie_title=title,
        special_only=True, hide_past=noon, hide_sold_out=True,
    )
    for s in filtered:
        assert s.chain in (CGV, MEGABOX)
        assert s.movie_title == title
        assert s.screen_type != service.GENERAL_SCREEN
        assert s.start >= noon
        assert s.seats_left > 0


def test_sorting():
    showtimes = service.collect_showtimes(service.default_sources(), TARGET, "서울").showtimes
    by_time = service.sort_showtimes(showtimes, by="time")
    assert [s.start for s in by_time] == sorted(s.start for s in showtimes)
    by_seats = service.sort_showtimes(showtimes, by="seats")
    assert [s.seats_left for s in by_seats] == sorted((s.seats_left for s in showtimes), reverse=True)
