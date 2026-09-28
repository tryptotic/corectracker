#!/usr/bin/env python3
"""Log Purdue RecWell live facility counts to data/counts.csv.

Only appends a row when a location's LastUpdatedDateAndTime has changed, so
running this more often than the site updates (~hourly) creates no duplicates.
"""
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount"
API_KEY = os.environ.get("CREC_API_KEY", "aedeaf92-036d-4848-980b-7eb5526ea40c")
CSV_PATH = Path(os.environ.get("CREC_CSV", "data/counts.csv"))
FIELDS = ["updated_at", "fetched_at_utc", "location_id", "location",
          "count", "capacity", "pct_full"]


def fetch():
    r = requests.get(
        URL,
        params={"AccountAPIKey": API_KEY},
        headers={"User-Agent": "personal-gym-crowd-logger"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def last_seen():
    seen = {}
    if CSV_PATH.exists():
        with CSV_PATH.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seen[row["location_id"]] = row["updated_at"]
    return seen


def main():
    data = fetch()
    seen = last_seen()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for loc in data:
        if loc.get("IsClosed"):
            continue
        lid = str(loc["LocationId"])
        updated = loc["LastUpdatedDateAndTime"]
        if seen.get(lid) == updated:
            continue
        cap = loc["TotalCapacity"] or 0
        count = loc["LastCount"]
        pct = round(100 * count / cap, 1) if cap else ""
        rows.append({
            "updated_at": updated,          # Purdue local (Indiana) time
            "fetched_at_utc": now,
            "location_id": lid,
            "location": loc["LocationName"].strip(),
            "count": count,
            "capacity": cap,
            "pct_full": pct,
        })

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} new rows ({len(data)} locations returned)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # don't fail noisily; next run will catch up
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
