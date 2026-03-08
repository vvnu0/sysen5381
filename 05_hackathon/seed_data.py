import os
import random
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)

RESET = True  # set to False if you do not want to wipe old test data

locs = [
    {"name": "1st Ave & Main St", "area": "Downtown", "road_type": "intersection", "latitude": 40.7128, "longitude": -74.0060, "bias": 18},
    {"name": "Broadway & 7th", "area": "Midtown", "road_type": "intersection", "latitude": 40.7580, "longitude": -73.9855, "bias": 22},
    {"name": "River Pkwy Segment A", "area": "West Side", "road_type": "segment", "latitude": 40.7300, "longitude": -73.9950, "bias": 12},
    {"name": "Central Ave & Pine", "area": "Uptown", "road_type": "intersection", "latitude": 40.7450, "longitude": -73.9700, "bias": 10},
    {"name": "East Loop Segment B", "area": "East Side", "road_type": "segment", "latitude": 40.7350, "longitude": -73.9550, "bias": 15},
    {"name": "Market St & 3rd", "area": "Downtown", "road_type": "intersection", "latitude": 40.7100, "longitude": -74.0010, "bias": 20},
    {"name": "Harbor Rd Segment C", "area": "Harbor", "road_type": "segment", "latitude": 40.7000, "longitude": -74.0150, "bias": 14},
    {"name": "University Ave & Oak", "area": "Campus", "road_type": "intersection", "latitude": 40.7290, "longitude": -73.9965, "bias": 8},
]

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def make_rows(loc_id, bias, days=30):
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    ts_list = pd.date_range(start=start, end=end, freq="15min", tz="UTC")

    rows = []
    for ts in ts_list:
        hr = ts.hour
        wd = ts.weekday()

        rush = 25 if hr in [7, 8, 9, 16, 17, 18] else 0
        weekend = -10 if wd >= 5 else 0
        event = 15 if ts.day % 11 == 0 and hr in [17, 18, 19] else 0

        base = 35 + bias + rush + weekend + event + random.gauss(0, 8)
        cong = clamp(round(base), 0, 100)
        speed = max(5, round(45 - 0.28 * cong + random.gauss(0, 2), 1))
        delay = max(0, round(1.7 * cong + random.gauss(0, 10)))

        rows.append({
            "location_id": loc_id,
            "ts": ts.to_pydatetime(),
            "congestion_level": cong,
            "avg_speed_mph": speed,
            "delay_seconds": delay,
            "source": "synthetic"
        })
    return rows

with engine.begin() as conn:
    if RESET:
        conn.execute(text("truncate table public.locations restart identity cascade"))

    for loc in locs:
        conn.execute(
            text("""
                insert into public.locations (name, area, road_type, latitude, longitude)
                values (:name, :area, :road_type, :latitude, :longitude)
                on conflict (name) do nothing
            """),
            {
                "name": loc["name"],
                "area": loc["area"],
                "road_type": loc["road_type"],
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
            }
        )

    rows = conn.execute(text("select id, name from public.locations order by id")).fetchall()
    id_map = {row.name: row.id for row in rows}

all_rows = []
for loc in locs:
    all_rows.extend(make_rows(id_map[loc["name"]], loc["bias"]))

df = pd.DataFrame(all_rows)

df.to_sql(
    "congestion_readings",
    engine,
    schema="public",
    if_exists="append",
    index=False,
    method="multi",
    chunksize=1000,
)

print(f"Inserted {len(df)} congestion readings.")
print("Done. Refresh the Supabase Table Editor to see the data.")
