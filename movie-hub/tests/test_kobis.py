from datetime import date

import pytest

from sources import kobis

TARGET = date(2026, 11, 12)


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_without_key_returns_sample(monkeypatch):
    monkeypatch.delenv("KOBIS_API_KEY", raising=False)
    entries = kobis.fetch_daily_box_office(TARGET)
    assert entries[0].movie_title.startswith("[샘플]")


def test_parses_kobis_response(monkeypatch):
    monkeypatch.setenv("KOBIS_API_KEY", "test-key")
    data = {"boxOfficeResult": {"dailyBoxOfficeList": [
        {"rank": "1", "movieNm": "영화A", "audiCnt": "12372", "audiAcc": "32505", "openDt": "2026-11-11"},
        {"rank": "2", "movieNm": "영화B", "audiCnt": "9902", "audiAcc": "213784", "openDt": " "},
    ]}}
    monkeypatch.setattr(kobis.requests, "get", lambda *a, **k: FakeResponse(data))

    entries = kobis.fetch_daily_box_office(TARGET)
    assert [e.rank for e in entries] == [1, 2]
    assert entries[0].daily_audience == 12372
    assert entries[0].open_date == date(2026, 11, 11)
    assert entries[1].open_date is None  # 개봉일이 비어 있는 영화


def test_invalid_key_raises_error(monkeypatch):
    monkeypatch.setenv("KOBIS_API_KEY", "wrong-key")
    data = {"faultInfo": {"message": "유효하지않은 키값입니다.", "errorCode": "320010"}}
    monkeypatch.setattr(kobis.requests, "get", lambda *a, **k: FakeResponse(data))

    with pytest.raises(RuntimeError, match="유효하지않은 키값"):
        kobis.fetch_daily_box_office(TARGET)
