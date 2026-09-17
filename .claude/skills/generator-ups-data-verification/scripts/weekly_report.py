#!/usr/bin/env python
"""
Reads the Verification Log tab, groups entries by ISO week, and renders a line
chart of Accuracy % over time plus a short text summary. Pure local rendering
only - does not touch Google Drive itself. The calling session (a scheduled
task, per generator-ups-data-verification's weekly reporting step) is
responsible for reading this script's output and uploading it via the Drive
connector, since MCP tools aren't callable from a plain Python script.

Usage:
    python weekly_report.py <SHEET_ID> <OUTPUT_DIR>

Writes:
    <OUTPUT_DIR>/verification_accuracy_chart.png
    <OUTPUT_DIR>/verification_accuracy_summary.txt
"""
import csv
import io
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
SHEETS_API_SH = SCRIPT_DIR.parent.parent / "generator-ups-data-enrichment" / "scripts" / "sheets_api.sh"


def fetch_log_rows(sheet_id: str):
    result = subprocess.run(
        ["bash", str(SHEETS_API_SH), "read", sheet_id, "Verification Log!A2:F"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return data.get("values", [])


def week_key(date_str: str) -> str:
    dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def main():
    sheet_id = sys.argv[1]
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = fetch_log_rows(sheet_id)
    weekly_accuracies = defaultdict(list)
    total_batches = 0

    for row in rows:
        if len(row) < 6 or not row[0].strip():
            continue
        try:
            wk = week_key(row[0])
            accuracy = float(str(row[5]).replace("%", "").strip())
        except (ValueError, IndexError):
            continue
        weekly_accuracies[wk].append(accuracy)
        total_batches += 1

    weeks_sorted = sorted(weekly_accuracies.keys())

    summary_path = out_dir / "verification_accuracy_summary.txt"
    chart_path = out_dir / "verification_accuracy_chart.png"

    if not weeks_sorted:
        summary_path.write_text(
            "No verification data logged yet - the Verification Log tab is empty "
            "or has no rows with a valid Date and Accuracy %% this week. This is "
            "expected before the enrichment/verification pipeline has run any "
            "batches yet.",
            encoding="utf-8",
        )
        # Still emit a placeholder chart so the report file always exists.
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.text(0.5, 0.5, "No verification data yet", ha="center", va="center", fontsize=14)
        ax.axis("off")
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"NO_DATA\n{chart_path}\n{summary_path}")
        return

    week_avgs = [sum(weekly_accuracies[w]) / len(weekly_accuracies[w]) for w in weeks_sorted]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(weeks_sorted, week_avgs, marker="o", linewidth=2, color="#2e6f95")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Accuracy %")
    ax.set_xlabel("Week")
    ax.set_title("Aurias 2 Market Map - Verification Accuracy Over Time")
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)

    latest_week = weeks_sorted[-1]
    latest_avg = week_avgs[-1]
    latest_batches = len(weekly_accuracies[latest_week])
    trend = ""
    if len(week_avgs) >= 2:
        delta = week_avgs[-1] - week_avgs[-2]
        direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
        trend = f" Accuracy is {direction} {abs(delta):.1f} points versus the previous week."

    summary = (
        f"Verification accuracy report, week {latest_week}.\n\n"
        f"This week: {latest_avg:.1f}% average accuracy across {latest_batches} "
        f"verified batch(es).{trend}\n\n"
        f"Total batches logged to date: {total_batches}, across {len(weeks_sorted)} week(s).\n"
    )
    summary_path.write_text(summary, encoding="utf-8")

    print(f"OK\n{chart_path}\n{summary_path}")


if __name__ == "__main__":
    main()
