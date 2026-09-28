#!/usr/bin/env python3
"""Log selected Purdue RecWell facility counts to data/counts.csv.

Only appends a row when a location's LastUpdatedDateAndTime has changed.
"""

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


URL = "https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount"

API_KEY = os.environ.get(
    "CREC_API_KEY",
    "aedeaf92-036d-4848-980b-7eb5526ea40c"
)

CSV_PATH = Path(
    os.environ.get("CREC_CSV", "data/counts.csv")
)

FIELDS = [
    "updated_at",
    "fetched_at_utc",
    "location_id",
    "location",
    "count",
    "capacity",
    "pct_full",
]

TRACK = {
    6130: "MAC Court",
    5995: "Upper Fitness",
    6157: "East Mezzanine",
    6158: "West Mezzanine",
    5981: "Fitness Loft",
    5993: "Scifres",
    5972: "Climbing Wall",
    5969: "Bouldering Wall",
    11620: "East Fitness",
    7290: "Colby Fitness",
    5985: "Lower Gym",
}


def fetch():
    response = requests.get(
        URL,
        params={"AccountAPIKey": API_KEY},
        headers={"User-Agent": "personal-gym-crowd-logger"},
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def last_seen():
    seen = {}

    if CSV_PATH.exists():
        with CSV_PATH.open(
            newline="",
            encoding="utf-8"
        ) as f:

            for row in csv.DictReader(f):
                seen[row["location_id"]] = row["updated_at"]

    return seen


def main():
    data = fetch()
    seen = last_seen()

    now = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    rows = []

    for loc in data:

        lid = int(loc["LocationId"])

        if lid not in TRACK:
            continue

        if loc.get("IsClosed"):
            continue

        updated = loc["LastUpdatedDateAndTime"]

        if seen.get(str(lid)) == updated:
            continue

        capacity = loc["TotalCapacity"] or 0
        count = loc["LastCount"]

        pct = (
            round(100 * count / capacity, 1)
            if capacity
            else ""
        )

        rows.append({
            "updated_at": updated,
            "fetched_at_utc": now,
            "location_id": lid,
            "location": TRACK[lid],
            "count": count,
            "capacity": capacity,
            "pct_full": pct,
        })

    CSV_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    new_file = not CSV_PATH.exists()

    with CSV_PATH.open(
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS
        )

        if new_file:
            writer.writeheader()

        writer.writerows(rows)

    print(
        f"{len(rows)} new rows "
        f"({len(data)} locations returned)"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        print(
            f"error: {e}",
            file=sys.stderr
        )
        sys.exit(1)
