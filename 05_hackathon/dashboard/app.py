import os
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="City Congestion Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("City Congestion Tracker")
st.caption("Explore current congestion, historical trends, typical daily patterns, baseline comparisons, and AI summaries.")


def api_get(path: str, params: dict[str, Any] | None = None, timeout: int = 30):
    url = f"{API_URL}{path}"
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict[str, Any], timeout: int = 90):
    url = f"{API_URL}{path}"
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300)
def get_locations():
    return api_get("/locations")


@st.cache_data(ttl=30)
def get_current(minutes: int, limit: int):
    return api_get("/congestion/current", {"minutes": minutes, "limit": limit})


@st.cache_data(ttl=30)
def get_history(location_id: int, hours: int):
    return api_get("/congestion/history", {"location_id": location_id, "hours": hours})


@st.cache_data(ttl=30)
def get_pattern(days: int, location_id: int | None, area: str | None):
    params: dict[str, Any] = {"days": days}
    if location_id is not None:
        params["location_id"] = location_id
    if area:
        params["area"] = area
    return api_get("/congestion/pattern", params)


@st.cache_data(ttl=30)
def get_compare(window_hours: int, baseline_days: int, location_id: int | None, area: str | None):
    params: dict[str, Any] = {
        "window_hours": window_hours,
        "baseline_days": baseline_days,
    }
    if location_id is not None:
        params["location_id"] = location_id
    if area:
        params["area"] = area
    return api_get("/congestion/compare", params)


def to_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def scope_filter_label(scope_mode: str, area: str | None, location_name: str | None) -> str:
    if scope_mode == "All locations":
        return "All locations"
    if scope_mode == "Area" and area:
        return f"Area: {area}"
    if scope_mode == "Single location" and location_name:
        return f"Location: {location_name}"
    return "All locations"


def build_scope_params(scope_mode: str, area: str | None, location_id: int | None):
    compare_location_id = None
    compare_area = None
    summary_location_ids = None
    summary_area = None

    if scope_mode == "Area" and area:
        compare_area = area
        summary_area = area
    elif scope_mode == "Single location" and location_id is not None:
        compare_location_id = location_id
        summary_location_ids = [location_id]

    return compare_location_id, compare_area, summary_location_ids, summary_area


# ---------- Load metadata ----------
try:
    health = api_get("/health")
    api_ok = health.get("status") == "ok"
except Exception as e:
    api_ok = False
    health_error = str(e)

if not api_ok:
    st.error(f"Could not connect to the API at {API_URL}. Error: {health_error}")
    st.stop()

loc_rows = get_locations()
loc_df = to_df(loc_rows)

if loc_df.empty:
    st.error("No locations were returned by the API.")
    st.stop()

loc_df = loc_df.sort_values(["area", "name"]).reset_index(drop=True)

areas = sorted(loc_df["area"].dropna().unique().tolist())
loc_name_to_id = dict(zip(loc_df["name"], loc_df["id"]))
loc_id_to_name = dict(zip(loc_df["id"], loc_df["name"]))

# ---------- Sidebar ----------
with st.sidebar:
    st.success(f"API connected: {API_URL}")

    st.subheader("Analysis Scope")
    scope_mode = st.radio(
        "Choose what the analysis should focus on",
        ["All locations", "Area", "Single location"],
        index=0,
    )

    selected_area = None
    selected_scope_location_name = None
    selected_scope_location_id = None

    if scope_mode == "Area":
        selected_area = st.selectbox("Select area", areas)
    elif scope_mode == "Single location":
        selected_scope_location_name = st.selectbox("Select location", loc_df["name"].tolist())
        selected_scope_location_id = loc_name_to_id[selected_scope_location_name]

    st.divider()

    st.subheader("Controls")
    current_minutes = st.slider("Current congestion window (minutes)", 15, 240, 60, 15)
    history_hours = st.slider("History window (hours)", 24, 24 * 30, 24 * 7, 24)
    pattern_days = st.slider("Pattern window (days)", 1, 30, 7, 1)
    compare_window_hours = st.slider("Compare current window (hours)", 1, 24, 2, 1)
    baseline_days = st.slider("Historical baseline (days)", 2, 60, 14, 1)
    top_n = st.slider("Top rows / summary locations", 3, 10, 5, 1)

scope_text = scope_filter_label(scope_mode, selected_area, selected_scope_location_name)
compare_location_id, compare_area, summary_location_ids, summary_area = build_scope_params(
    scope_mode,
    selected_area,
    selected_scope_location_id,
)

st.info(f"Current scope: **{scope_text}**")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Current Snapshot",
        "Location History",
        "Typical Daily Pattern",
        "Current vs Usual",
        "AI Summary",
    ]
)

# ---------- Tab 1: Current Snapshot ----------
with tab1:
    st.subheader("Worst congestion right now")

    try:
        cur_rows = get_current(current_minutes, 50)
        cur_df = to_df(cur_rows)
    except Exception as e:
        st.error(f"Failed to load current congestion data: {e}")
        cur_df = pd.DataFrame()

    if not cur_df.empty:
        if scope_mode == "Area" and selected_area:
            cur_df = cur_df[cur_df["area"] == selected_area].copy()
        elif scope_mode == "Single location" and selected_scope_location_id is not None:
            cur_df = cur_df[cur_df["location_id"] == selected_scope_location_id].copy()

        cur_df = cur_df.sort_values("avg_congestion", ascending=False).head(top_n).reset_index(drop=True)

        if cur_df.empty:
            st.warning("No current congestion rows matched this scope.")
        else:
            worst_name = cur_df.iloc[0]["name"]
            worst_val = float(cur_df.iloc[0]["avg_congestion"])
            mean_val = round(float(cur_df["avg_congestion"].mean()), 1)

            c1, c2, c3 = st.columns(3)
            c1.metric("Locations shown", len(cur_df))
            c2.metric("Average congestion", mean_val)
            c3.metric("Worst location", f"{worst_name} ({worst_val})")

            show_df = cur_df.rename(
                columns={
                    "name": "Location",
                    "area": "Area",
                    "avg_congestion": "Avg Congestion",
                    "avg_speed_mph": "Avg Speed (mph)",
                    "avg_delay_seconds": "Avg Delay (sec)",
                }
            )
            st.dataframe(
                show_df[["Location", "Area", "Avg Congestion", "Avg Speed (mph)", "Avg Delay (sec)"]],
                use_container_width=True,
                hide_index=True,
            )

            chart_df = cur_df[["name", "avg_congestion"]].set_index("name")
            st.bar_chart(chart_df)
    else:
        st.warning("No current congestion data returned by the API.")

# ---------- Tab 2: Location History ----------
with tab2:
    st.subheader("Recent history for one location")

    history_options = loc_df["name"].tolist()

    if scope_mode == "Area" and selected_area:
        history_options = loc_df.loc[loc_df["area"] == selected_area, "name"].tolist()
    elif scope_mode == "Single location" and selected_scope_location_name:
        history_options = [selected_scope_location_name]

    history_location_name = st.selectbox(
        "Choose a location to inspect",
        history_options,
        key="history_location_name",
    )
    history_location_id = loc_name_to_id[history_location_name]

    try:
        hist_rows = get_history(history_location_id, history_hours)
        hist_df = to_df(hist_rows)
    except Exception as e:
        st.error(f"Failed to load history: {e}")
        hist_df = pd.DataFrame()

    if hist_df.empty:
        st.warning("No history rows returned for this location.")
    else:
        hist_df["ts"] = pd.to_datetime(hist_df["ts"], utc=True)
        hist_df = hist_df.sort_values("ts")

        latest = hist_df.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Latest congestion", latest["congestion_level"])
        c2.metric("Latest speed (mph)", latest["avg_speed_mph"])
        c3.metric("Latest delay (sec)", latest["delay_seconds"])

        chart_df = hist_df.set_index("ts")[["congestion_level", "avg_speed_mph", "delay_seconds"]]
        st.line_chart(chart_df)

        with st.expander("Show raw history data"):
            st.dataframe(hist_df, use_container_width=True, hide_index=True)

# ---------- Tab 3: Typical Daily Pattern ----------
with tab3:
    st.subheader("Typical congestion by hour of day")

    try:
        pat_rows = get_pattern(
            days=pattern_days,
            location_id=compare_location_id,
            area=compare_area,
        )
        pat_df = to_df(pat_rows)
    except Exception as e:
        st.error(f"Failed to load pattern data: {e}")
        pat_df = pd.DataFrame()

    if pat_df.empty:
        st.warning("No pattern rows matched this scope.")
    else:
        pat_df = pat_df.sort_values("hour").reset_index(drop=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Average congestion by hour**")
            st.line_chart(pat_df.set_index("hour")[["avg_congestion"]])
        with c2:
            st.markdown("**Average speed and delay by hour**")
            st.line_chart(pat_df.set_index("hour")[["avg_speed_mph", "avg_delay_seconds"]])

        with st.expander("Show hourly pattern table"):
            show_pat = pat_df.rename(
                columns={
                    "hour": "Hour",
                    "avg_congestion": "Avg Congestion",
                    "avg_speed_mph": "Avg Speed (mph)",
                    "avg_delay_seconds": "Avg Delay (sec)",
                    "sample_count": "Samples",
                }
            )
            st.dataframe(show_pat, use_container_width=True, hide_index=True)

# ---------- Tab 4: Current vs Usual ----------
with tab4:
    st.subheader("Current conditions vs historical baseline")

    try:
        cmp = get_compare(
            window_hours=compare_window_hours,
            baseline_days=baseline_days,
            location_id=compare_location_id,
            area=compare_area,
        )
    except Exception as e:
        st.error(f"Failed to load comparison data: {e}")
        cmp = None

    if not cmp:
        st.warning("Comparison data could not be loaded.")
    else:
        overall = cmp.get("overall", {}) or {}
        by_loc = to_df(cmp.get("by_location", []))
        rises = to_df(cmp.get("biggest_rises", []))
        drops = to_df(cmp.get("biggest_drops", []))

        c1, c2, c3 = st.columns(3)
        c1.metric("Current avg congestion", overall.get("current_avg_congestion"))
        c2.metric("Historical avg congestion", overall.get("historical_avg_congestion"))
        c3.metric("Delta / status", f'{overall.get("delta")} ({overall.get("status")})')

        if by_loc.empty:
            st.warning("No per-location comparison rows matched this scope.")
        else:
            view_df = by_loc.rename(
                columns={
                    "name": "Location",
                    "area": "Area",
                    "current_avg_congestion": "Current Avg",
                    "historical_avg_congestion": "Historical Avg",
                    "delta": "Delta",
                    "status": "Status",
                    "current_avg_speed_mph": "Current Speed",
                    "historical_avg_speed_mph": "Historical Speed",
                    "current_avg_delay_seconds": "Current Delay",
                    "historical_avg_delay_seconds": "Historical Delay",
                }
            )

            st.dataframe(
                view_df[
                    [
                        "Location",
                        "Area",
                        "Current Avg",
                        "Historical Avg",
                        "Delta",
                        "Status",
                        "Current Speed",
                        "Historical Speed",
                        "Current Delay",
                        "Historical Delay",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            delta_chart = by_loc[["name", "delta"]].copy().set_index("name")
            st.markdown("**Congestion change by location**")
            st.bar_chart(delta_chart)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Biggest rises**")
                if rises.empty:
                    st.write("No rise data.")
                else:
                    st.dataframe(rises[["name", "delta"]], use_container_width=True, hide_index=True)

            with c2:
                st.markdown("**Biggest drops**")
                if drops.empty:
                    st.write("No drop data.")
                else:
                    st.dataframe(drops[["name", "delta"]], use_container_width=True, hide_index=True)

# ---------- Tab 5: AI Summary ----------
with tab5:
    st.subheader("AI-generated congestion summary")

    summary_payload: dict[str, Any] = {
        "window_hours": compare_window_hours,
        "baseline_days": baseline_days,
        "top_n": top_n,
    }
    if summary_area:
        summary_payload["area"] = summary_area
    if summary_location_ids:
        summary_payload["location_ids"] = summary_location_ids

    st.caption(
        "This sends aggregated congestion stats to Ollama Cloud and returns a short operator-facing summary."
    )

    summary_key = f"{scope_mode}|{selected_area}|{selected_scope_location_id}|{compare_window_hours}|{baseline_days}|{top_n}"

    if "summary_result" not in st.session_state:
        st.session_state["summary_result"] = None
        st.session_state["summary_key"] = None

    if st.button("Generate AI summary", type="primary"):
        try:
            with st.spinner("Generating summary..."):
                result = api_post("/summary", summary_payload, timeout=120)
            st.session_state["summary_result"] = result
            st.session_state["summary_key"] = summary_key
        except Exception as e:
            st.error(f"Failed to generate summary: {e}")

    if st.session_state.get("summary_key") == summary_key and st.session_state.get("summary_result"):
        result = st.session_state["summary_result"]

        st.markdown("### Summary")
        st.write(result.get("summary", "No summary returned."))

        model = result.get("model")
        if model:
            st.caption(f"Model: {model}")

        stats = result.get("stats", {})
        by_loc = to_df(stats.get("by_location", []))
        if not by_loc.empty:
            st.markdown("### Supporting comparison data")
            st.dataframe(
                by_loc[
                    [
                        "name",
                        "area",
                        "current_avg_congestion",
                        "historical_avg_congestion",
                        "delta",
                        "status",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Click the button to generate a summary for the current scope and time window.")