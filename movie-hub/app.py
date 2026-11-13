"""영화관 통합 시간표 - 화면.

실행: streamlit run app.py
"""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from core import service
from core.models import ALL_CHAINS
from sources import kobis

load_dotenv()

st.set_page_config(page_title="영화관 통합 시간표", page_icon="🎬", layout="wide")
st.title("🎬 영화관 통합 시간표")

sources = service.default_sources()

# ---------------- 왼쪽 메뉴 (조건 선택) ----------------
with st.sidebar:
    st.header("조건 선택")
    today = date.today()
    target_date = st.date_input("날짜", value=today, min_value=today, max_value=today + timedelta(days=13))
    region = st.selectbox("지역", ["서울"])
    chains = st.multiselect("영화관", ALL_CHAINS, default=ALL_CHAINS)
    special_only = st.checkbox("특별관만 보기 (IMAX, 4DX, Dolby 등)")
    hide_sold_out = st.checkbox("매진 회차 숨기기")
    sort_by = st.radio("정렬", ["시간순", "남은 좌석 많은 순"], horizontal=True)

    st.divider()
    st.caption("데이터 상태")
    for source in sources:
        st.caption(f"{'🟢 실제' if source.is_live else '🟡 샘플'} · {source.chain}")
    st.caption(f"{'🟢 실제' if kobis.has_api_key() else '🟡 샘플'} · 박스오피스(KOBIS)")


@st.cache_data(ttl=600, show_spinner="상영시간표를 불러오는 중...")
def load_showtimes(target_date: date, region: str):
    # 10분 동안은 같은 결과를 재사용 (영화관 서버에 부담을 주지 않기 위해)
    return service.collect_showtimes(service.default_sources(), target_date, region)


@st.cache_data(ttl=3600, show_spinner="박스오피스를 불러오는 중...")
def load_box_office(target_date: date):
    # 불러온 시각도 함께 저장 (화면에 '언제 받아온 정보인지' 표시하기 위해)
    return kobis.fetch_daily_box_office(target_date), datetime.now()


WEEKDAYS = "월화수목금토일"


# ---------------- 박스오피스 ----------------
yesterday = date.today() - timedelta(days=1)
st.subheader("📊 박스오피스 TOP 10")
try:
    box_office, fetched_at = load_box_office(yesterday)
    st.caption(
        f"🗓️ 집계 기준: {yesterday:%Y-%m-%d}({WEEKDAYS[yesterday.weekday()]}) 하루 전체 (00:00 ~ 24:00)"
        f" · 🔄 불러온 시각: {fetched_at:%m/%d %H:%M} · 출처: 영화진흥위원회 KOBIS"
    )
    st.dataframe(
        pd.DataFrame(
            {
                "순위": e.rank,
                "영화": e.movie_title,
                "일일 관객": f"{e.daily_audience:,}명",
                "누적 관객": f"{e.total_audience:,}명",
                "개봉일": e.open_date,
            }
            for e in box_office
        ),
        hide_index=True,
        width="stretch",
    )
except Exception as e:
    st.error(f"박스오피스를 불러오지 못했습니다: {e}")

# ---------------- 상영시간표 ----------------
st.subheader("🕐 상영시간표")
result = load_showtimes(target_date, region)
for chain, message in result.errors.items():
    st.warning(f"{chain} 시간표를 불러오지 못했습니다: {message}")

titles = service.movie_titles(result.showtimes)
movie = st.selectbox("영화 선택", ["전체 영화", *titles])

showtimes = service.filter_showtimes(
    result.showtimes,
    chains=chains,
    movie_title=None if movie == "전체 영화" else movie,
    special_only=special_only,
    hide_past=datetime.now() if target_date == date.today() else None,
    hide_sold_out=hide_sold_out,
)
showtimes = service.sort_showtimes(showtimes, by="seats" if sort_by == "남은 좌석 많은 순" else "time")

if not showtimes:
    st.info("조건에 맞는 상영 회차가 없습니다. 왼쪽 조건을 바꿔 보세요.")
else:
    st.caption(f"총 {len(showtimes)}개 회차")
    st.dataframe(
        pd.DataFrame(
            {
                "시작": s.start.strftime("%H:%M"),
                "종료": s.end.strftime("%H:%M"),
                "영화관": s.chain,
                "극장": s.theater,
                "영화": s.movie_title,
                "상영관": s.screen_type,
                "잔여석": f"{s.seats_left} / {s.total_seats}",
                "예매": s.booking_url,
            }
            for s in showtimes
        ),
        hide_index=True,
        width="stretch",
        column_config={"예매": st.column_config.LinkColumn("예매", display_text="예매하기")},
    )
