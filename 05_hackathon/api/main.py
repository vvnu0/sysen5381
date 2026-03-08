import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text

load_dotenv()

db_url = os.getenv("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "https://ollama.com/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

app = FastAPI(title="City Congestion API")


class SummaryRequest(BaseModel):
    window_hours: int = 2
    baseline_days: int = 14
    location_ids: list[int] | None = None
    area: str | None = None
    top_n: int = 5


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def classify_delta(delta: float, tol: float = 5.0) -> str:
    if delta >= tol:
        return "worse"
    if delta <= -tol:
        return "better"
    return "similar"


def build_filters(
    location_id: int | None = None,
    location_ids: list[int] | None = None,
    area: str | None = None,
    table_alias_r: str = "r",
    table_alias_l: str = "l",
):
    clauses = []
    params: dict[str, Any] = {}

    if location_id is not None:
        clauses.append(f"{table_alias_r}.location_id = :location_id")
        params["location_id"] = location_id

    if location_ids:
        ph = []
        for i, val in enumerate(location_ids):
            key = f"loc_{i}"
            ph.append(f":{key}")
            params[key] = int(val)
        clauses.append(f"{table_alias_r}.location_id in ({', '.join(ph)})")

    if area:
        clauses.append(f"{table_alias_l}.area = :area")
        params["area"] = area

    where_sql = ""
    if clauses:
        where_sql = " and " + " and ".join(clauses)

    return where_sql, params


def get_current_stats(
    window_hours: int = 2,
    location_id: int | None = None,
    location_ids: list[int] | None = None,
    area: str | None = None,
):
    extra_sql, params = build_filters(location_id, location_ids, area)
    params["window_hours"] = window_hours

    q = text(f"""
        select
            l.id as location_id,
            l.name,
            l.area,
            round(avg(r.congestion_level)::numeric, 1) as avg_congestion,
            round(avg(r.avg_speed_mph)::numeric, 1) as avg_speed_mph,
            round(avg(r.delay_seconds)::numeric, 1) as avg_delay_seconds,
            count(*) as sample_count
        from public.congestion_readings r
        join public.locations l on l.id = r.location_id
        where r.ts >= now() - (:window_hours * interval '1 hour')
        {extra_sql}
        group by l.id, l.name, l.area
        order by avg_congestion desc, l.name
    """)

    with engine.connect() as conn:
        rows = conn.execute(q, params).mappings().all()
    return rows_to_dicts(rows)


def hours_in_window(window_hours: int) -> list[int]:
    now = datetime.now(timezone.utc)
    out = []
    for i in range(window_hours):
        out.append((now - timedelta(hours=i)).hour)
    return sorted(set(out))


def get_baseline_stats(
    window_hours: int = 2,
    baseline_days: int = 14,
    location_id: int | None = None,
    location_ids: list[int] | None = None,
    area: str | None = None,
):
    hrs = hours_in_window(window_hours)
    hour_keys = []
    hour_params: dict[str, Any] = {}

    for i, h in enumerate(hrs):
        k = f"h_{i}"
        hour_keys.append(f":{k}")
        hour_params[k] = h

    extra_sql, params = build_filters(location_id, location_ids, area)
    params.update(hour_params)
    params["baseline_days"] = baseline_days
    params["window_hours"] = window_hours

    q = text(f"""
        select
            l.id as location_id,
            l.name,
            l.area,
            round(avg(r.congestion_level)::numeric, 1) as baseline_congestion,
            round(avg(r.avg_speed_mph)::numeric, 1) as baseline_speed_mph,
            round(avg(r.delay_seconds)::numeric, 1) as baseline_delay_seconds,
            count(*) as sample_count
        from public.congestion_readings r
        join public.locations l on l.id = r.location_id
        where r.ts >= now() - (:baseline_days * interval '1 day')
          and r.ts <  now() - (:window_hours * interval '1 hour')
          and extract(hour from r.ts) in ({", ".join(hour_keys)})
          {extra_sql}
        group by l.id, l.name, l.area
        order by baseline_congestion desc, l.name
    """)

    with engine.connect() as conn:
        rows = conn.execute(q, params).mappings().all()
    return rows_to_dicts(rows)


def build_compare_payload(
    window_hours: int = 2,
    baseline_days: int = 14,
    location_id: int | None = None,
    location_ids: list[int] | None = None,
    area: str | None = None,
):
    cur = get_current_stats(window_hours, location_id, location_ids, area)
    base = get_baseline_stats(window_hours, baseline_days, location_id, location_ids, area)

    base_map = {row["location_id"]: row for row in base}
    by_location = []

    for row in cur:
        b = base_map.get(row["location_id"])

        cur_val = float(row["avg_congestion"])
        base_val = float(b["baseline_congestion"]) if b and b["baseline_congestion"] is not None else None
        delta = round(cur_val - base_val, 1) if base_val is not None else None

        item = {
            "location_id": row["location_id"],
            "name": row["name"],
            "area": row["area"],
            "current_avg_congestion": cur_val,
            "historical_avg_congestion": base_val,
            "delta": delta,
            "status": classify_delta(delta) if delta is not None else "no-baseline",
            "current_avg_speed_mph": float(row["avg_speed_mph"]) if row["avg_speed_mph"] is not None else None,
            "historical_avg_speed_mph": float(b["baseline_speed_mph"]) if b and b["baseline_speed_mph"] is not None else None,
            "current_avg_delay_seconds": float(row["avg_delay_seconds"]) if row["avg_delay_seconds"] is not None else None,
            "historical_avg_delay_seconds": float(b["baseline_delay_seconds"]) if b and b["baseline_delay_seconds"] is not None else None,
        }
        by_location.append(item)

    if by_location:
        cur_overall = round(sum(x["current_avg_congestion"] for x in by_location) / len(by_location), 1)
        hist_vals = [x["historical_avg_congestion"] for x in by_location if x["historical_avg_congestion"] is not None]
        hist_overall = round(sum(hist_vals) / len(hist_vals), 1) if hist_vals else None
        overall_delta = round(cur_overall - hist_overall, 1) if hist_overall is not None else None
        overall_status = classify_delta(overall_delta) if overall_delta is not None else "no-baseline"
    else:
        cur_overall = None
        hist_overall = None
        overall_delta = None
        overall_status = "no-data"

    biggest_rises = sorted(
        [x for x in by_location if x["delta"] is not None],
        key=lambda x: x["delta"],
        reverse=True,
    )[:5]

    biggest_drops = sorted(
        [x for x in by_location if x["delta"] is not None],
        key=lambda x: x["delta"],
    )[:5]

    return {
        "window_hours": window_hours,
        "baseline_days": baseline_days,
        "overall": {
            "current_avg_congestion": cur_overall,
            "historical_avg_congestion": hist_overall,
            "delta": overall_delta,
            "status": overall_status,
        },
        "by_location": by_location,
        "biggest_rises": biggest_rises,
        "biggest_drops": biggest_drops,
    }


def ollama_chat(messages: list[dict[str, str]]) -> str:
    if not OLLAMA_API_KEY:
        raise HTTPException(status_code=500, detail="OLLAMA_API_KEY is missing")

    body = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(OLLAMA_URL, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama request failed: {e}") from e
    except KeyError as e:
        raise HTTPException(status_code=502, detail="Unexpected Ollama response shape") from e


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/locations")
def get_locations():
    q = text("""
        select id, name, area, road_type, latitude, longitude
        from public.locations
        order by name
    """)
    with engine.connect() as conn:
        rows = conn.execute(q).mappings().all()
    return rows_to_dicts(rows)


@app.get("/congestion/current")
def get_current(
    minutes: int = Query(60, ge=15, le=1440),
    limit: int = Query(10, ge=1, le=50),
):
    q = text("""
        select
            l.id as location_id,
            l.name,
            l.area,
            round(avg(r.congestion_level)::numeric, 1) as avg_congestion,
            round(avg(r.avg_speed_mph)::numeric, 1) as avg_speed_mph,
            round(avg(r.delay_seconds)::numeric, 1) as avg_delay_seconds
        from public.congestion_readings r
        join public.locations l on l.id = r.location_id
        where r.ts >= now() - (:minutes * interval '1 minute')
        group by l.id, l.name, l.area
        order by avg_congestion desc
        limit :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"minutes": minutes, "limit": limit}).mappings().all()
    return rows_to_dicts(rows)


@app.get("/congestion/history")
def get_history(
    location_id: int,
    hours: int = Query(168, ge=1, le=24 * 60),
):
    q = text("""
        select ts, congestion_level, avg_speed_mph, delay_seconds
        from public.congestion_readings
        where location_id = :location_id
          and ts >= now() - (:hours * interval '1 hour')
        order by ts
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"location_id": location_id, "hours": hours}).mappings().all()
    return rows_to_dicts(rows)


@app.get("/congestion/pattern")
def get_pattern(
    days: int = Query(7, ge=1, le=90),
    location_id: int | None = None,
    area: str | None = None,
):
    extra_sql, params = build_filters(location_id=location_id, area=area)
    params["days"] = days

    q = text(f"""
        select
            extract(hour from r.ts)::int as hour,
            round(avg(r.congestion_level)::numeric, 1) as avg_congestion,
            round(avg(r.avg_speed_mph)::numeric, 1) as avg_speed_mph,
            round(avg(r.delay_seconds)::numeric, 1) as avg_delay_seconds,
            count(*) as sample_count
        from public.congestion_readings r
        join public.locations l on l.id = r.location_id
        where r.ts >= now() - (:days * interval '1 day')
        {extra_sql}
        group by hour
        order by hour
    """)

    with engine.connect() as conn:
        rows = conn.execute(q, params).mappings().all()
    return rows_to_dicts(rows)


@app.get("/congestion/compare")
def get_compare(
    window_hours: int = Query(2, ge=1, le=24),
    baseline_days: int = Query(14, ge=2, le=90),
    location_id: int | None = None,
    area: str | None = None,
):
    return build_compare_payload(
        window_hours=window_hours,
        baseline_days=baseline_days,
        location_id=location_id,
        area=area,
    )


@app.post("/summary")
def get_summary(req: SummaryRequest):
    compare = build_compare_payload(
        window_hours=req.window_hours,
        baseline_days=req.baseline_days,
        location_ids=req.location_ids,
        area=req.area,
    )

    by_loc = compare["by_location"][: req.top_n]
    if not by_loc:
        return {
            "summary": "No congestion data matched the selected filters.",
            "stats": compare,
        }

    prompt_data = {
        "window_hours": req.window_hours,
        "baseline_days": req.baseline_days,
        "overall": compare["overall"],
        "top_locations_now": [
            {
                "name": x["name"],
                "area": x["area"],
                "current_avg_congestion": x["current_avg_congestion"],
                "historical_avg_congestion": x["historical_avg_congestion"],
                "delta": x["delta"],
                "status": x["status"],
            }
            for x in by_loc
        ],
        "biggest_rises": [
            {
                "name": x["name"],
                "delta": x["delta"],
            }
            for x in compare["biggest_rises"][: req.top_n]
        ],
        "biggest_drops": [
            {
                "name": x["name"],
                "delta": x["delta"],
            }
            for x in compare["biggest_drops"][: req.top_n]
        ],
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are an operations analyst for a city transportation authority. "
                "Write a concise, actionable congestion summary in 3 to 5 sentences. "
                "Focus on which areas are worst now, whether conditions are above or below normal, "
                "and one concrete watch-out or avoidance recommendation. "
                "Do not invent facts that are not in the provided data."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize this congestion snapshot for city operators:\n{prompt_data}",
        },
    ]

    summary = ollama_chat(messages)

    return {
        "summary": summary,
        "stats": compare,
        "model": OLLAMA_MODEL,
    }