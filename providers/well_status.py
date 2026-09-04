#!/usr/bin/env python3
"""Print a compact freshness status for the well level sensor."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import water_report


def main() -> int:
    max_age_minutes = int(os.getenv("WATER_STATUS_MAX_AGE_MINUTES", "15"))
    now = datetime.now(timezone.utc)
    try:
        measurements = water_report._fetch(
            now - timedelta(minutes=max_age_minutes), now
        )
        valid, _ = water_report._filter(measurements)
    except Exception:
        print("❌ Колодец")
        return 0

    if not valid:
        print("❌ Колодец")
        return 0

    print("✅ Колодец")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

