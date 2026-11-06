"""Synthetic A350 CAMO audit demonstration using SQLite.

This educational example is not an approved maintenance program and must not
be used to make airworthiness, dispatch, or maintenance decisions.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta


# Demonstration values only. Real limits and intervals must come from approved,
# current aircraft and engine documentation and the operator's procedures.
DEMO_EGT_LIMIT_C = 10.0
DEMO_EGT_DEGRADATION_C_PER_1000_HOURS = 1.5
DEMO_HPT_CYCLE_LIMIT = 4500


def initialize_demo_db() -> sqlite3.Connection:
    """Create an in-memory database populated with clearly synthetic records."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE aircraft (
            tail_number TEXT PRIMARY KEY,
            msn INTEGER NOT NULL UNIQUE,
            delivery_year INTEGER NOT NULL,
            airframe_hours REAL NOT NULL,
            airframe_cycles INTEGER NOT NULL,
            next_c_check_due TEXT NOT NULL
        );
        CREATE TABLE engines (
            esn TEXT PRIMARY KEY,
            tail_number TEXT NOT NULL REFERENCES aircraft(tail_number),
            position TEXT NOT NULL,
            engine_hours REAL NOT NULL,
            engine_cycles INTEGER NOT NULL,
            egt_margin_c REAL NOT NULL,
            hpt_disk_cycles INTEGER NOT NULL
        );
        CREATE TABLE composite_repairs (
            repair_id TEXT PRIMARY KEY,
            tail_number TEXT NOT NULL REFERENCES aircraft(tail_number),
            ata_chapter TEXT NOT NULL,
            location TEXT NOT NULL,
            srm_reference TEXT NOT NULL,
            last_ndt_date TEXT NOT NULL,
            next_ndt_due TEXT NOT NULL
        );
        CREATE TABLE directives (
            directive_id TEXT PRIMARY KEY,
            description TEXT NOT NULL
        );
        CREATE TABLE directive_compliance (
            directive_id TEXT NOT NULL REFERENCES directives(directive_id),
            tail_number TEXT NOT NULL REFERENCES aircraft(tail_number),
            engineering_order TEXT,
            PRIMARY KEY (directive_id, tail_number)
        );
        """
    )

    # Synthetic fleet identifiers and measurements for software demonstration.
    tails = [f"OH-LW{chr(code)}" for code in range(ord("A"), ord("S"))]
    for index, tail in enumerate(tails):
        hours = 42_000.0 - index * 1_800.0
        cycles = int(hours / 6.4)
        conn.execute(
            "INSERT INTO aircraft VALUES (?, ?, ?, ?, ?, ?)",
            (tail, 1000 + index, 2015 + index // 3, hours, cycles,
             f"{2027 + index % 2}-06-15"),
        )
        for position_number, position in ((1, "ENG1_LH"), (2, "ENG2_RH")):
            engine_hours = hours * 0.75
            engine_cycles = int(engine_hours / 6.4)
            margin = max(8.0, 68.0 - engine_hours / 1000 * 1.35)
            hpt_cycles = engine_cycles
            if tail == "OH-LWC" and position == "ENG2_RH":
                margin = 7.8
            if tail == "OH-LWG" and position == "ENG1_LH":
                hpt_cycles = 4_530
            conn.execute(
                "INSERT INTO engines VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"DEMO-XWB-{index * 2 + position_number:03d}", tail, position,
                 engine_hours, engine_cycles, round(margin, 1), hpt_cycles),
            )

    conn.executemany(
        "INSERT INTO composite_repairs VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("DEMO-REP-014", "OH-LWA", "ATA 57", "RH outer wing lower skin",
             "DEMO-SRM-57-11-04", "2024-05-10", "2026-05-10"),
            ("DEMO-REP-028", "OH-LWE", "ATA 53", "rear fuselage panel",
             "DEMO-SRM-53-81-01", "2025-08-20", "2027-08-20"),
        ],
    )
    conn.executemany(
        "INSERT INTO directives VALUES (?, ?)",
        [
            ("DEMO-AD-001", "Illustrative engine-control software directive"),
            ("DEMO-AD-002", "Illustrative wing inspection directive"),
        ],
    )
    # Create a compliance row for each aircraft/directive; blank EO means the
    # synthetic record is missing evidence and should be reviewed in the demo.
    for tail in tails:
        for directive_id in ("DEMO-AD-001", "DEMO-AD-002"):
            eo = f"DEMO-EO-{directive_id[-3:]}-{tail[-1]}"
            if directive_id == "DEMO-AD-002" and tail == "OH-LWD":
                eo = None
            conn.execute(
                "INSERT INTO directive_compliance VALUES (?, ?, ?)",
                (directive_id, tail, eo),
            )
    conn.commit()
    return conn


def forecast_egt_limit(
    current_margin_c: float,
    current_engine_hours: float,
    utilization_hours_per_year: float = 4_000.0,
    degradation_c_per_1000_hours: float = DEMO_EGT_DEGRADATION_C_PER_1000_HOURS,
    threshold_c: float = DEMO_EGT_LIMIT_C,
    today: date | None = None,
) -> date | None:
    """Estimate when the demonstration EGT threshold is reached.

    Returns None if the threshold is already reached or input rates are invalid.
    This simple linear estimate is not an engine health model.
    """
    if current_margin_c <= threshold_c or utilization_hours_per_year <= 0:
        return None
    if degradation_c_per_1000_hours <= 0:
        return None
    hours_remaining = (current_margin_c - threshold_c) / (
        degradation_c_per_1000_hours / 1000.0
    )
    days_remaining = round(hours_remaining / utilization_hours_per_year * 365.25)
    return (today or date.today()) + timedelta(days=days_remaining)


def run_audit(conn: sqlite3.Connection, as_of: date | None = None) -> list[dict[str, str]]:
    """Return findings against the configurable demonstration thresholds."""
    as_of = as_of or date.today()
    findings: list[dict[str, str]] = []

    for row in conn.execute(
        "SELECT * FROM engines WHERE egt_margin_c <= ?", (DEMO_EGT_LIMIT_C,)
    ):
        findings.append({
            "severity": "REVIEW",
            "category": "EGT_THRESHOLD",
            "tail": row["tail_number"],
            "item": f"{row['position']} ({row['esn']})",
            "detail": f"Demo EGT margin {row['egt_margin_c']:.1f}°C; threshold {DEMO_EGT_LIMIT_C:.1f}°C",
        })

    for row in conn.execute(
        "SELECT * FROM engines WHERE hpt_disk_cycles >= ?", (DEMO_HPT_CYCLE_LIMIT,)
    ):
        findings.append({
            "severity": "REVIEW",
            "category": "LLP_CYCLE_THRESHOLD",
            "tail": row["tail_number"],
            "item": f"HPT Stage 1 disk ({row['esn']})",
            "detail": f"Demo cycles {row['hpt_disk_cycles']}; threshold {DEMO_HPT_CYCLE_LIMIT}",
        })

    for row in conn.execute(
        "SELECT * FROM composite_repairs WHERE next_ndt_due < ?", (as_of.isoformat(),)
    ):
        findings.append({
            "severity": "REVIEW",
            "category": "NDT_DATE_PASSED",
            "tail": row["tail_number"],
            "item": f"{row['repair_id']} — {row['ata_chapter']} {row['location']}",
            "detail": f"Demo NDT date passed: {row['next_ndt_due']} ({row['srm_reference']})",
        })

    for row in conn.execute(
        """SELECT c.tail_number, d.directive_id, d.description
           FROM directive_compliance AS c
           JOIN directives AS d USING (directive_id)
           WHERE c.engineering_order IS NULL OR trim(c.engineering_order) = ''"""
    ):
        findings.append({
            "severity": "REVIEW",
            "category": "DIRECTIVE_EVIDENCE_MISSING",
            "tail": row["tail_number"],
            "item": row["directive_id"],
            "detail": f"No demo EO reference recorded: {row['description']}",
        })
    return findings


def print_report(conn: sqlite3.Connection, findings: list[dict[str, str]], as_of: date) -> None:
    fleet = conn.execute(
        "SELECT COUNT(*) AS count, AVG(airframe_hours) AS hours, AVG(airframe_cycles) AS cycles FROM aircraft"
    ).fetchone()
    engines = conn.execute("SELECT COUNT(*) FROM engines").fetchone()[0]
    print("A350 CAMO AUDIT — SYNTHETIC DEMONSTRATION")
    print(f"As of: {as_of.isoformat()}")
    print("This report is not approved maintenance or airworthiness guidance.\n")
    print(f"Demo fleet: {fleet['count']} aircraft | {engines} engines")
    print(f"Average airframe time: {fleet['hours']:,.0f} FH | {fleet['cycles']:,.0f} FC")
    print(f"Findings: {len(findings)}\n")
    for number, finding in enumerate(findings, start=1):
        print(
            f"{number:02d}. [{finding['severity']}] {finding['category']} — "
            f"{finding['tail']} / {finding['item']}\n    {finding['detail']}"
        )
    print("\nEGT forecast examples (linear planning estimate only):")
    for row in conn.execute("SELECT * FROM engines ORDER BY egt_margin_c LIMIT 3"):
        forecast = forecast_egt_limit(row["egt_margin_c"], row["engine_hours"])
        label = forecast.isoformat() if forecast else "threshold already reached"
        print(f"  {row['tail_number']} {row['position']}: {label}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(),
                        help="Audit date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()
    conn = initialize_demo_db()
    try:
        print_report(conn, run_audit(conn, args.as_of), args.as_of)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
