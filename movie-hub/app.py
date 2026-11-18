"""영화관 통합 시간표 - 화면.

실행: streamlit run app.py
"""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from core import service
from core.models import ALL_CHAINS
from core.theaters import district_of
from sources import kobis

load_dotenv()

st.set_page_config(page_title="영화관 통합 시간표", page_icon="🎬", layout="wide")
st.title("🎬 영화관 통합 시간표")

sources = service.default_sources()

# 시간대 버튼 -> 시간 범위 (24 이상은 다음 날 새벽. 예: 26 = 다음 날 02시)
TIME_PRESETS = {"전체": (5, 30), "오전": (5, 12), "오후": (12, 17), "저녁": (17, 21), "심야": (21, 30)}
HOURS = list(range(5, 31))


def hour_label(h: int) -> str:
    return f"{h % 24:02d}:00" + (" (다음날)" if h >= 24 else "")


# hour_range: 지금 선택된 시간 범위 (버튼과 슬라이더가 함께 바라보는 값)
# slider_version: 버튼을 누를 때마다 슬라이더를 새로 그려서 범위를 맞추기 위한 번호
st.session_state.setdefault("time_preset", "전체")
st.session_state.setdefault("hour_range", TIME_PRESETS["전체"])
st.session_state.setdefault("slider_version", 0)


def slider_key() -> str:
    return f"hour_slider_{st.session_state.slider_version}"


def on_preset_change():
    # 시간대 버튼을 누르면 슬라이더도 그 범위로 맞춘다
    if st.session_state.time_preset:
        st.session_state.hour_range = TIME_PRESETS[st.session_state.time_preset]
        st.session_state.slider_version += 1


def on_slider_change():
    # 슬라이더를 직접 움직이면 버튼 선택은 해제 (범위가 버튼과 같으면 그 버튼을 켠다)
    st.session_state.hour_range = st.session_state[slider_key()]
    matched = [k for k, v in TIME_PRESETS.items() if v == st.session_state.hour_range]
    st.session_state.time_preset = matched[0] if matched else None

# ---------------- 왼쪽 메뉴 (조건 선택) ----------------
with st.sidebar:
    st.header("조건 선택")
    today = date.today()
    target_date = st.date_input("날짜", value=today, min_value=today, max_value=today + timedelta(days=13))
    region = st.selectbox("지역", ["서울"])
    chains = st.multiselect("영화관", ALL_CHAINS, default=ALL_CHAINS)
    district_slot = st.empty()  # 구 목록은 시간표를 불러온 뒤에 채운다

    st.markdown("**⏰ 시간대**")
    st.segmented_control(
        "시간대", list(TIME_PRESETS), key="time_preset", on_change=on_preset_change, label_visibility="collapsed"
    )
    hour_range = st.select_slider(
        "시작 시간 범위",
        options=HOURS,
        value=st.session_state.hour_range,
        key=slider_key(),
        format_func=hour_label,
        on_change=on_slider_change,
    )

    special_only = st.checkbox("특별관만 보기 (IMAX, 4DX, Dolby 등)")
    bookable_only = st.checkbox("예약 가능한 회차만 보기", value=True, help="예매 마감·매진된 회차는 숨깁니다")
    sort_by = st.radio("정렬 (전체 목록)", ["시간순", "남은 좌석 많은 순"], horizontal=True)

    st.divider()
    st.caption("데이터 상태")
    for source in sources:
        st.caption(f"{'🟢 실제' if source.is_live else '🔴 연결 불가'} · {source.chain}")
    st.caption(f"{'🟢 실제' if kobis.has_api_key() else '🟡 샘플'} · 박스오피스(KOBIS)")


@st.cache_data(ttl=600, show_spinner="영화관에서 상영시간표를 불러오는 중... (10초 정도 걸려요)")
def load_showtimes(target_date: date, region: str):
    # 10분 동안은 같은 결과를 재사용 (영화관 서버에 부담을 주지 않기 위해)
    return service.collect_showtimes(service.default_sources(), target_date, region), datetime.now()


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
result, showtimes_fetched_at = load_showtimes(target_date, region)
st.caption(f"🔄 불러온 시각: {showtimes_fetched_at:%m/%d %H:%M} · 10분마다 새로 불러옵니다 (남은 좌석은 그사이 바뀔 수 있어요)")
for source in sources:
    if source.notice and source.chain in chains:
        st.info(source.notice)
for chain, message in result.errors.items():
    st.warning(f"{chain} 시간표를 불러오지 못했습니다: {message}")

with district_slot:
    all_districts = service.district_list(result.showtimes)
    picked_districts = st.multiselect("📍 구 (비우면 전체)", all_districts, placeholder="전체 구")

titles = service.movie_titles(result.showtimes)
movie = st.selectbox("영화 선택", ["전체 영화", *titles])

midnight = datetime.combine(target_date, datetime.min.time())
showtimes = service.filter_showtimes(
    result.showtimes,
    chains=chains,
    movie_title=None if movie == "전체 영화" else movie,
    special_only=special_only,
    hide_past=datetime.now() if target_date == date.today() else None,
    bookable_only=bookable_only,
    start_between=(midnight + timedelta(hours=hour_range[0]), midnight + timedelta(hours=hour_range[1])),
    districts=picked_districts or None,
)


def showtime_table(rows):
    return pd.DataFrame(
        {
            "시작": s.start.strftime("%H:%M"),
            "종료": s.end.strftime("%H:%M"),
            "구": district_of(s.chain, s.theater),
            "영화관": s.chain,
            "극장": s.theater,
            "영화": s.movie_title,
            "상영관": s.screen_name,
            "종류": s.screen_type,
            "잔여석": f"{s.seats_left} / {s.total_seats}",
            "예매": s.booking_url,
        }
        for s in rows
    )


LINK_COLUMN = {"예매": st.column_config.LinkColumn("예매", display_text="예매하기")}

st.caption(
    f"{hour_label(hour_range[0])} ~ {hour_label(hour_range[1])} 시작 · "
    f"{'예약 가능한 ' if bookable_only else ''}회차 {len(showtimes)}개 · "
    f"극장 {len({service.theater_label(s) for s in showtimes})}곳"
)
if not showtimes:
    st.info("조건에 맞는 상영 회차가 없습니다. 왼쪽 조건을 바꿔 보세요.")
    st.stop()

tab_list, tab_hours, tab_districts = st.tabs(["📋 전체 목록", "⏰ 시간대별 표", "📍 구별 보기"])

# ---------------- 탭 1: 전체 목록 ----------------
with tab_list:
    rows = service.sort_showtimes(showtimes, by="seats" if sort_by == "남은 좌석 많은 순" else "time")
    st.dataframe(showtime_table(rows), hide_index=True, width="stretch", column_config=LINK_COLUMN)

# ---------------- 탭 2: 시간대별 표 (극장 x 시간) ----------------
with tab_hours:
    st.caption("숫자 = 그 시간대에 시작하는 회차 수 · 줄을 누르면 아래에 그 극장의 회차가 나옵니다")
    counts = service.count_by_theater_and_hour(showtimes, target_date)
    hours = list(range(hour_range[0], hour_range[1]))
    pivot = pd.DataFrame(
        [[by_hour.get(h, 0) for h in hours] for by_hour in counts.values()],
        index=[f"{district} · {theater}" for district, theater in counts],
        columns=[hour_label(h).replace(":00", "시") for h in hours],
    )
    pivot = pivot.loc[:, pivot.sum() > 0]  # 회차가 하나도 없는 시간 열은 숨김
    peak = max(pivot.to_numpy().max(), 1)
    styled = pivot.style.format(lambda v: v or "").map(
        lambda v: f"background-color: rgba(229, 9, 20, {0.15 + 0.6 * v / peak:.2f})" if v else ""
    )
    picked = st.dataframe(styled, width="stretch", on_select="rerun", selection_mode="single-row", key="hour_table")
    if picked.selection.rows:
        label = pivot.index[picked.selection.rows[0]]
        theater = label.split(" · ", 1)[1]
        st.markdown(f"**{label}** 회차")
        rows = [s for s in showtimes if service.theater_label(s) == theater]
        st.dataframe(showtime_table(rows), hide_index=True, width="stretch", column_config=LINK_COLUMN)

# ---------------- 탭 3: 구별 보기 ----------------
with tab_districts:
    groups = service.group_by_district(showtimes)
    for district, theaters in groups.items():
        n_showtimes = sum(len(v) for v in theaters.values())
        with st.expander(f"**{district}** · 극장 {len(theaters)}곳 · 회차 {n_showtimes}개", expanded=len(groups) <= 3):
            for theater, rows in theaters.items():
                st.markdown(f"**[{theater}]({rows[0].booking_url})**")
                by_movie: dict[str, list] = {}
                for s in rows:
                    by_movie.setdefault(s.movie_title, []).append(s)
                for title, movie_rows in by_movie.items():
                    times = " · ".join(f"{s.start:%H:%M}({s.seats_left}석)" for s in movie_rows)
                    st.markdown(f"- {title}: {times}")
