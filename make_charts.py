#!/usr/bin/env python3
"""Turn data/counts.csv into heatmaps, hourly line charts, and best-time lists.

Usage:  python make_charts.py [--csv data/counts.csv] [--hours 6-22] [--min-samples 2]
Outputs: heatmaps.png, hourly_lines.png, best_times.csv (and prints the top 3
quietest day/hour slots per facility).
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# LocationId -> label. Edit this dict to add/remove facilities.
TRACK = {
    6130: "MAC Court", 5995: "Upper Fitness", 6157: "East Mezzanine",
    6158: "West Mezzanine", 5981: "Fitness Loft", 5993: "Scifres",
    5972: "Climbing Wall", 5969: "Bouldering Wall", 11620: "East Fitness",
    7290: "Colby Fitness", 5985: "Lower Gym",
}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load(path, lo, hi):
    df = pd.read_csv(path, parse_dates=["updated_at"])
    df = df[df["location_id"].isin(TRACK)].copy()
    df["name"] = df["location_id"].map(TRACK)
    df["dow"] = df["updated_at"].dt.dayofweek
    df["hour"] = df["updated_at"].dt.hour
    df = df[(df["hour"] >= lo) & (df["hour"] <= hi)]
    return df


def grid(n, cols=3):
    rows = -(-n // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 4 * rows))
    axes = axes.flatten()
    for ax in axes[n:]:
        ax.axis("off")
    return fig, axes


def heatmaps(df, lo, hi):
    names = list(TRACK.values())
    fig, axes = grid(len(names))
    hours = list(range(lo, hi + 1))
    for ax, name in zip(axes, names):
        d = df[df["name"] == name]
        pv = (d.pivot_table(index="dow", columns="hour", values="pct_full", aggfunc="mean")
                .reindex(index=range(7), columns=hours))
        im = ax.imshow(pv.values, aspect="auto", cmap="YlOrRd", vmin=0)
        ax.set_title(name)
        ax.set_yticks(range(7))
        ax.set_yticklabels(DAYS)
        ax.set_xticks(range(0, len(hours), 2))
        ax.set_xticklabels(hours[::2])
        fig.colorbar(im, ax=ax, label="% full")
    fig.suptitle("Average % full by day and hour (lighter = quieter)", y=1.0)
    fig.tight_layout()
    fig.savefig("heatmaps.png", dpi=130)


def lines(df):
    names = list(TRACK.values())
    fig, axes = grid(len(names))
    for ax, name in zip(axes, names):
        d = df[df["name"] == name].copy()
        d["daytype"] = d["dow"].map(lambda x: "Weekend" if x >= 5 else "Weekday")
        for label, g in d.groupby("daytype"):
            s = g.groupby("hour")["pct_full"].mean()
            ax.plot(s.index, s.values, marker="o", label=label)
        ax.set_title(name)
        ax.set_xlabel("hour")
        ax.set_ylabel("% full")
        ax.legend()
    fig.tight_layout()
    fig.savefig("hourly_lines.png", dpi=130)


def best_times(df, min_samples):
    g = (df.groupby(["name", "dow", "hour"])["pct_full"]
           .agg(mean="mean", n="count").reset_index())
    g = g[g["n"] >= min_samples]
    out = []
    for name in TRACK.values():
        top = g[g["name"] == name].nsmallest(3, "mean")
        print(f"\n{name}")
        for _, r in top.iterrows():
            print(f"  {DAYS[int(r.dow)]} {int(r.hour):02d}:00  ~{r['mean']:.0f}% full (n={int(r.n)})")
        out.append(top)
    pd.concat(out).to_csv("best_times.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/counts.csv")
    ap.add_argument("--hours", default="6-22", help="hour range to consider, e.g. 6-22")
    ap.add_argument("--min-samples", type=int, default=2)
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.hours.split("-"))
    df = load(a.csv, lo, hi)
    if df.empty:
        raise SystemExit("No data yet for the tracked facilities.")
    heatmaps(df, lo, hi)
    lines(df)
    best_times(df, a.min_samples)
    print("\nSaved heatmaps.png, hourly_lines.png, best_times.csv")


if __name__ == "__main__":
    main()
