#!/usr/bin/env python3
"""Print fresh Nest temperature and humidity readings from YDB."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import ydb


LOCATIONS = (("floor_1", "1"), ("floor_2", "2"))


def utc_literal(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def safe_table_name(value: str) -> str:
    if not value or not all(character.isalnum() or character == "_" for character in value):
        raise ValueError("YDB_TABLE must contain only letters, digits, and underscores")
    return value


def format_reading(floor: str, row: object | None) -> str:
    if row is None or not bool(row.online):
        return f"⚠️ Дом, {floor} этаж: нет данных"
    return (
        f"🌡 Дом, {floor} этаж: {float(row.temperature_c):.1f} °C"
        f" · влажность {int(row.humidity_percent)}%"
    )


def latest_readings() -> dict[str, object]:
    max_age = int(os.getenv("NEST_CLIMATE_MAX_AGE_MINUTES", "15"))
    table = safe_table_name(os.getenv("YDB_TABLE", "nest_environment_readings"))
    start = datetime.now(timezone.utc) - timedelta(minutes=max_age)
    query = f"""
        SELECT location, measured_at, temperature_c, humidity_percent, online
        FROM `{table}`
        WHERE measured_at >= Timestamp(\"{utc_literal(start)}\")
          AND location IN (\"floor_1\", \"floor_2\")
        ORDER BY measured_at DESC;
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
        latest: dict[str, object] = {}
        for row in result[0].rows:
            if row.location not in latest:
                latest[row.location] = row
        return latest
    finally:
        driver.stop()


def main() -> int:
    try:
        readings = latest_readings()
    except Exception:
        readings = {}
    for location, floor in LOCATIONS:
        print(format_reading(floor, readings.get(location)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
