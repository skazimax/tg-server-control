from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from providers.nest_temperature import (
    TEMPERATURE_TRAIT,
    THERMOSTAT_TYPE,
    ambient_temperature,
    format_temperature,
)


class NestTemperatureTest(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "NEST_DEVICE_ACCESS_PROJECT_ID": "project-id",
            "NEST_OAUTH_CLIENT_ID": "client-id",
            "NEST_OAUTH_CLIENT_SECRET": "client-secret",
            "NEST_OAUTH_REFRESH_TOKEN": "refresh-token",
        },
        clear=True,
    )
    def test_reads_first_thermostat_temperature(self) -> None:
        token_response = Mock()
        token_response.json.return_value = {"access_token": "access-token"}
        devices_response = Mock()
        devices_response.json.return_value = {
            "devices": [
                {
                    "type": THERMOSTAT_TYPE,
                    "traits": {
                        TEMPERATURE_TRAIT: {"ambientTemperatureCelsius": 22.5}
                    },
                }
            ]
        }
        session = Mock()
        session.post.return_value = token_response
        session.get.return_value = devices_response

        self.assertEqual(ambient_temperature(session), 22.5)
        token_response.raise_for_status.assert_called_once_with()
        devices_response.raise_for_status.assert_called_once_with()

    def test_formats_temperature(self) -> None:
        self.assertEqual(
            format_temperature(22.5, "Дом, 1 этаж"),
            "🌡 Дом, 1 этаж: 22.5 °C",
        )


if __name__ == "__main__":
    unittest.main()
