"""영화관 응답을 공통 형식으로 바꾸는 부분 점검 (실제 접속 없이, 응답 모양만 흉내 낸다)."""

from datetime import date, datetime

from sources import lotte, megabox
from sources.base import parse_play_time

TARGET = date(2026, 11, 18)


def test_late_night_time_goes_to_next_day():
    assert parse_play_time(TARGET, "19:30") == datetime(2026, 11, 18, 19, 30)
    assert parse_play_time(TARGET, "24:32") == datetime(2026, 11, 19, 0, 32)


def test_megabox_theater_list():
    page = """
    <button type="button" class="sel-city">서울</button>
    <li data-brch-no="1372"><a href="/theater?brchNo=1372" title="강남 상세보기">강남</a></li>
    <li data-brch-no="0081"><a href="/theater?brchNo=0081" title="x">픽쳐하우스&#40;휴관&#41;</a></li>
    <button type="button" class="sel-city">경기</button>
    <li data-brch-no="4121"><a href="/theater?brchNo=4121" title="x">고양스타필드</a></li>
    """
    theaters = megabox.parse_theater_list(page)
    assert theaters["서울"] == [("1372", "강남")]  # 휴관 극장은 제외
    assert theaters["경기"] == [("4121", "고양스타필드")]


def test_megabox_schedule():
    data = {"megaMap": {"movieFormList": [{
        "brchNo": "1351", "brchNm": "코엑스", "playDe": "20261118",
        "movieNm": "[굿즈패키지] 헝거게임", "rpstMovieNm": "헝거게임",
        "playStartTime": "23:50", "playEndTime": "26:38",
        "theabKindCd": "DBC", "theabExpoNm": "Dolby Cinema&#40;컴포트&#41;",
        "restSeatCnt": 12, "theabSeatCnt": 86,
    }]}}
    [s] = megabox.parse_schedule(data, TARGET, "서울")
    assert s.movie_title == "헝거게임"
    assert s.screen_type == "Dolby Cinema"
    assert s.screen_name == "Dolby Cinema(컴포트)"
    assert s.end == datetime(2026, 11, 19, 2, 38)
    assert (s.seats_left, s.total_seats) == (12, 86)
    assert "brchNo=1351" in s.booking_url
    assert s.bookable  # bokdAbleAt 이 없으면 예매 가능으로 본다

    data["megaMap"]["movieFormList"][0]["bokdAbleAt"] = "N"
    [closed] = megabox.parse_schedule(data, TARGET, "서울")
    assert not closed.bookable


def test_lotte_cinema_list():
    data = {
        "CinemaDivison": {"AreaDivisions": {"Items": [
            {"DivisionCode": 1, "DetailDivisionCode": "0001", "GroupNameKR": "서울"},
            {"DivisionCode": 2, "DetailDivisionCode": "0300", "GroupNameKR": "샤롯데"},
        ]}},
        "Cinemas": {"Cinemas": {"Items": [
            {"DivisionCode": 1, "DetailDivisionCode": "0001", "CinemaID": 1016, "CinemaNameKR": "월드타워"},
            {"DivisionCode": 2, "DetailDivisionCode": "0300", "CinemaID": 1016, "CinemaNameKR": "월드타워"},
        ]}},
    }
    assert lotte.parse_cinema_list(data) == {"서울": [("1|0001|1016", "월드타워")]}


def test_lotte_play_sequence():
    data = {"PlaySeqs": {"Items": [
        {"CinemaNameKR": "월드타워", "MovieNameKR": "폭설", "StartTime": "22:50", "EndTime": "24:32",
         "ScreenDivisionNameKR": "샤롯데", "ScreenNameKR": "1관 샤롯데",
         "BookingSeatCount": 20, "TotalSeatCount": 32, "IsBookingYN": "N"},
        {"CinemaNameKR": "월드타워", "MovieNameKR": "폭설", "StartTime": None, "EndTime": None},
    ]}}
    [s] = lotte.parse_play_sequence(data, TARGET, "서울", "1|0001|1016")
    assert s.screen_type == "샤롯데"
    assert s.end == datetime(2026, 11, 19, 0, 32)
    assert (s.seats_left, s.total_seats) == (20, 32)
    assert "cinemaID=1016" in s.booking_url
    assert not s.bookable
