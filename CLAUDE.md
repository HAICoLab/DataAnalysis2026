# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

`DataAnalysis2026` is a **public** repo (`HAICoLab/DataAnalysis2026`) that holds projects as top-level folders. Currently the only project is `movie-hub/`: a Streamlit app that merges Seoul showtimes from 메가박스, 롯데시네마 and CGV into one view, plus KOBIS daily box office. UI text, code comments, README and commit messages are in Korean (commit subject style: `movie-hub: <요약>`).

## Commands

All commands run from `movie-hub/` (`pytest.ini` sets `pythonpath = .`, so imports like `from core import service` only resolve from there). The environment is miniconda, not venv.

```bash
conda env create -f environment.yml          # once; installs requirements.txt via pip
conda activate movie-hub                     # or prefix commands with: conda run -n movie-hub
streamlit run app.py                         # http://localhost:8501
pytest                                       # all tests (offline, no network)
pytest tests/test_parsers.py::test_megabox_schedule   # single test
```

Add dependencies to `requirements.txt` (not `environment.yml`). No linter/formatter is configured.

`KOBIS_API_KEY` goes in `movie-hub/.env` (gitignored; see `.env.example`). Without it the box office falls back to sample data.

## Architecture

Data flows `sources/*` → `core/models.Showtime` → `core/service` → `app.py`.

- **`sources/base.ShowtimeSource`** is the contract every chain implements: `chain`, `is_live` (drives the 🟢/🔴 status in the sidebar), optional `notice` (shown as an info box), and `fetch_showtimes(date, region) -> list[Showtime]`. Each source keeps network calls in `fetch_showtimes` and the conversion in pure module-level `parse_*` functions; tests exercise only the `parse_*` functions with inline fake responses and never hit the network.
- **`PoliteSession`** (in `sources/base.py`) wraps every request with a 0.3s delay; `app.py` caches showtimes for 10 minutes (`st.cache_data(ttl=600)`). These are deliberate limits on load against the cinema sites — don't lower them.
- **Late-night times**: the cinemas write times past midnight as `24:32`, `26:10`. `parse_play_time` turns these into next-day datetimes, and the app's time slider and `count_by_theater_and_hour` use hour values 24–30 for the same reason.
- **`service.collect_showtimes`** runs all sources in parallel threads. A failing source is recorded in `CollectResult.errors` and the app shows a warning, while the other chains still render.
- **Screen types**: `filter_showtimes(special_only=True)` keeps anything whose `screen_type != "일반"`. Seat-only variants (Megabox `RCL`/`CFT`, Lotte `리클라이너`) are mapped to `"일반"` in each source (`megabox.SCREEN_TYPES`, `lotte.GENERAL_SCREENS`). Map new codes there, or they will show up as special screens.
- **Districts (구)**: `core/theaters.THEATER_DISTRICTS` is a hand-maintained map from `(chain, theater name)` to 구. Theater names must match exactly what the source returns. Unknown theaters become `"구 미정"`. Only the 서울 region is supported end to end.
- **`bookable_only`** requires both the chain's own booking flag (`Showtime.bookable`) and `seats_left > 0`.

## Data sources

The sites have no official API. The sources replay the requests the sites' own pages make:

- **메가박스**: the theater list comes from parsing `/theater/list` HTML (split on `<button class="sel-city">` region headings; closed theaters are marked `휴관`). Showtimes come from a POST of JSON to `/on/oh/ohc/Brch/schedulePage.do`, one request per theater. Use `rpstMovieNm`, not `movieNm`, for titles (it drops tags like `[굿즈패키지]`). Theater addresses are at `/on/oh/ohc/Brch/infoPage.do`; the `/theater?brchNo=` page itself only contains the HQ address. robots.txt is `Disallow: /`, and README carries a personal/learning-use notice because of this.
- **롯데시네마**: everything is a POST to `/LCWS/Ticketing/TicketingData.aspx` with a multipart form field `paramList` holding JSON with a `MethodName`. `GetTicketingPageTOBE` returns cinemas (`DivisionCode == 1` means region grouping; the cinema id param is `"Division|DetailDivision|CinemaID"`). `GetPlaySequence` returns showtimes; `BookingSeatCount` is the number of **remaining** seats.
- **CGV**: Cloudflare returns a 403 "비정상적으로 접속" page to non-browser clients. `CgvSource` is intentionally link-only. Do not add code that bypasses this block.
- **KOBIS**: daily box office exists only up to yesterday. Errors come back as HTTP 200 with a `faultInfo` body, which `kobis.py` raises as `RuntimeError`.

## Streamlit gotcha

The time-slot buttons (`st.segmented_control`) and the range `st.select_slider` share state via `session_state.hour_range`. The slider must get `value=` explicitly and is re-keyed (`slider_version`) when a button is pressed. Setting a keyed select_slider's state from a callback without `value=` drops it into single-value mode and crashes on `hour_range[0]`.

When verifying UI changes headlessly, `streamlit.testing.v1.AppTest.from_file(<absolute path to app.py>)` works, but it hits the live sites. Dataframe row selection can't be simulated there.
