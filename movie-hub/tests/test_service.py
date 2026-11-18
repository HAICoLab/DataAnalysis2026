from datetime import date, datetime

from core import service
from core.models import ALL_CHAINS, CGV, LOTTE, MEGABOX, Showtime
from sources.base import ShowtimeSource
from sources.sample_data import sample_showtimes

TARGET = date(2026, 11, 13)


class SampleSource(ShowtimeSource):
    """실제 영화관에 접속하지 않고 샘플 시간표를 돌려주는 테스트용 수집기."""

    def __init__(self, chain):
        self.chain = chain

    def fetch_showtimes(self, target_date, region):
        return sample_showtimes(self.chain, target_date, region)


def sample_sources():
    return [SampleSource(chain) for chain in ALL_CHAINS]


def test_all_three_chains_return_showtimes():
    result = service.collect_showtimes(sample_sources(), TARGET, "서울")
    assert result.errors == {}
    assert {s.chain for s in result.showtimes} == {"CGV", "롯데시네마", "메가박스"}


def test_one_broken_source_does_not_stop_others():
    class BrokenSource(ShowtimeSource):
        chain = "고장난영화관"

        def fetch_showtimes(self, target_date, region):
            raise ConnectionError("접속 실패")

    sources = [BrokenSource(), *sample_sources()]
    result = service.collect_showtimes(sources, TARGET, "서울")
    assert "고장난영화관" in result.errors
    assert len(result.showtimes) > 0


def test_filters():
    showtimes = service.collect_showtimes(sample_sources(), TARGET, "서울").showtimes
    noon = datetime(2026, 11, 13, 12, 0)
    title = service.movie_titles(showtimes)[0]

    filtered = service.filter_showtimes(
        showtimes, chains=[CGV, MEGABOX], movie_title=title,
        special_only=True, hide_past=noon, bookable_only=True,
    )
    assert filtered
    for s in filtered:
        assert s.chain in (CGV, MEGABOX)
        assert s.movie_title == title
        assert s.screen_type != service.GENERAL_SCREEN
        assert s.start >= noon
        assert s.seats_left > 0


def test_sorting():
    showtimes = service.collect_showtimes(sample_sources(), TARGET, "서울").showtimes
    by_time = service.sort_showtimes(showtimes, by="time")
    assert [s.start for s in by_time] == sorted(s.start for s in showtimes)
    by_seats = service.sort_showtimes(showtimes, by="seats")
    assert [s.seats_left for s in by_seats] == sorted((s.seats_left for s in showtimes), reverse=True)


def make(chain, theater, hh, mm=0, seats=10, bookable=True, day=13):
    start = datetime(2026, 11, day, hh, mm)
    return Showtime(chain=chain, theater=theater, region="서울", movie_title="영화", start=start, end=start,
                    screen_type="일반", seats_left=seats, total_seats=100, booking_url="", bookable=bookable)


def test_bookable_only_hides_closed_and_sold_out():
    rows = [make(MEGABOX, "코엑스", 18), make(MEGABOX, "코엑스", 19, seats=0), make(MEGABOX, "코엑스", 20, bookable=False)]
    assert [s.start.hour for s in service.filter_showtimes(rows, bookable_only=True)] == [18]


def test_time_range_and_district_filters():
    rows = [make(MEGABOX, "코엑스", 17, 59), make(MEGABOX, "코엑스", 18), make(LOTTE, "월드타워", 20, 59),
            make(LOTTE, "월드타워", 21), make(LOTTE, "건대입구", 19)]
    in_range = service.filter_showtimes(rows, start_between=(datetime(2026, 11, 13, 18), datetime(2026, 11, 13, 21)))
    assert [(s.theater, s.start.strftime("%H:%M")) for s in in_range] == [("코엑스", "18:00"), ("월드타워", "20:59"), ("건대입구", "19:00")]

    gangnam_songpa = service.filter_showtimes(rows, districts=["강남구", "송파구"])
    assert {s.theater for s in gangnam_songpa} == {"코엑스", "월드타워"}


def test_count_by_theater_and_hour_counts_late_night_as_24_plus():
    rows = [make(MEGABOX, "코엑스", 18), make(MEGABOX, "코엑스", 18, 30), make(MEGABOX, "코엑스", 0, 30, day=14),
            make(LOTTE, "월드타워", 19)]
    counts = service.count_by_theater_and_hour(rows, TARGET)
    assert counts == {("강남구", "메가박스 코엑스"): {18: 2, 24: 1}, ("송파구", "롯데시네마 월드타워"): {19: 1}}


def test_group_by_district_puts_busiest_first_and_unknown_theater_separately():
    rows = [make(LOTTE, "월드타워", 19), make(MEGABOX, "송파파크하비오", 18), make(MEGABOX, "코엑스", 18),
            make(MEGABOX, "새로생긴극장", 20)]
    groups = service.group_by_district(rows)
    assert list(groups)[0] == "송파구"
    assert list(groups["송파구"]) == ["롯데시네마 월드타워", "메가박스 송파파크하비오"]
    assert "구 미정" in groups
