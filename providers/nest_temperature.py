#!/usr/bin/env python3
"""Read the ambient temperature from a Nest thermostat via the SDM API."""

from __future__ import annotations

import os
from typing import Any

import requests


TOKEN_URL = "https://oauth2.googleapis.com/token"
SDM_BASE_URL = "https://smartdevicemanagement.googleapis.com/v1"
THERMOSTAT_TYPE = "sdm.devices.types.THERMOSTAT"
TEMPERATURE_TRAIT = "sdm.devices.traits.Temperature"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def request_options() -> dict[str, Any]:
    options: dict[str, Any] = {"timeout": 20}
    proxy = os.environ.get("NEST_HTTPS_PROXY", "").strip()
    if proxy:
        options["proxies"] = {"http": proxy, "https": proxy}
    return options


def access_token(session: Any = requests) -> str:
    response = session.post(
        TOKEN_URL,
        data={
            "client_id": required_env("NEST_OAUTH_CLIENT_ID"),
            "client_secret": required_env("NEST_OAUTH_CLIENT_SECRET"),
            "refresh_token": required_env("NEST_OAUTH_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        },
        **request_options(),
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("OAuth response has no access_token")
    return token


def device_url(project_id: str, device_id: str) -> str:
    if device_id.startswith("enterprises/"):
        name = device_id
    else:
        name = f"enterprises/{project_id}/devices/{device_id}"
    return f"{SDM_BASE_URL}/{name}"


def thermostat(session: Any, project_id: str, token: str) -> dict[str, Any]:
    configured_id = os.environ.get("NEST_DEVICE_ID", "").strip()
    headers = {"Authorization": f"Bearer {token}"}
    if configured_id:
        response = session.get(
            device_url(project_id, configured_id),
            headers=headers,
            **request_options(),
        )
        response.raise_for_status()
        return response.json()

    response = session.get(
        f"{SDM_BASE_URL}/enterprises/{project_id}/devices",
        headers=headers,
        **request_options(),
    )
    response.raise_for_status()
    for device in response.json().get("devices", []):
        if device.get("type") == THERMOSTAT_TYPE:
            return device
    raise RuntimeError("No Nest thermostat was found")


def ambient_temperature(session: Any = requests) -> float:
    project_id = required_env("NEST_DEVICE_ACCESS_PROJECT_ID")
    device = thermostat(session, project_id, access_token(session))
    value = device.get("traits", {}).get(TEMPERATURE_TRAIT, {}).get(
        "ambientTemperatureCelsius"
    )
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise RuntimeError("Thermostat response has no ambient temperature")
    return float(value)


def format_temperature(value: float, label: str) -> str:
    return f"🌡 {label}: {value:g} °C"


def main() -> int:
    label = os.environ.get("NEST_STATUS_LABEL", "Дом, 1 этаж").strip()
    try:
        print(format_temperature(ambient_temperature(), label))
    except Exception:
        print(f"⚠️ {label}: нет данных")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
