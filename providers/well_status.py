#!/usr/bin/env python3
"""Return well sensor availability based on recent valid YDB measurements."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import ydb


def utc_literal(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def has_recent_measurement() -> bool:
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
        return bool(result[0].rows)
    finally:
        driver.stop()


def main() -> int:
    try:
        available = has_recent_measurement()
    except Exception:
        available = False
    print("✅ Колодец" if available else "❌ Колодец")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

