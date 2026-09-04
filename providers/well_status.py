#!/usr/bin/env python3
"""Return well sensor availability based on recent valid YDB measurements."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import ydb


def utc_literal(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def latest_measurement() -> int | None:
    max_age = int(os.getenv("WATER_STATUS_MAX_AGE_MINUTES", "15"))
    valid_min = int(os.getenv("VALID_MIN_CM", "20"))
    valid_max = int(os.getenv("VALID_MAX_CM", "500"))
    table = os.environ.get("YDB_TABLE", "mqtt_sonar1_db").replace("`", "``")
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=max_age)
    query = f"""
        SELECT dttm, val
        FROM `{table}`
        WHERE dttm >= Datetime(\"{utc_literal(start)}\")
          AND dttm < Datetime(\"{utc_literal(end)}\")
          AND val >= {valid_min}
          AND val <= {valid_max}
        ORDER BY dttm DESC
        LIMIT 1;
    """
    driver = ydb.Driver(
        ydb.DriverConfig(
            endpoint=os.environ["YDB_ENDPOINT"],
            database=os.environ["YDB_DATABASE"],
            credentials=ydb.credentials_from_env_variables(),
        )
    )
    try:
        driver.wait(timeout=15, fail_fast=True)
        result = ydb.QuerySessionPool(driver, size=1).execute_with_retries(query)
        rows = result[0].rows
        return int(rows[0].val) if rows else None
    finally:
        driver.stop()


def main() -> int:
    try:
        value = latest_measurement()
    except Exception:
        value = None
    if len(sys.argv) > 1 and sys.argv[1] == "level":
        if value is None:
            print("⚠️ Уровень воды в колодце: нет данных")
        else:
            print(f"💧 Уровень воды в колодце: {value} см")
    else:
        print("✅ Колодец" if value is not None else "❌ Колодец")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
