from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


PROVIDER_PATH = (
    Path(__file__).resolve().parents[1] / "providers" / "nest_climate_status.py"
)


class NestClimateStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with patch.dict("sys.modules", {"ydb": Mock()}):
            spec = importlib.util.spec_from_file_location(
                "nest_climate_status", PROVIDER_PATH
            )
            assert spec is not None and spec.loader is not None
            cls.provider = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.provider)

    def test_formats_temperature_and_humidity(self) -> None:
        row = SimpleNamespace(
            temperature_c=24.75,
            humidity_percent=52,
            online=True,
        )
        self.assertEqual(
            self.provider.format_reading("1", row),
            "🌡 Дом, 1 этаж: 24.8 °C · влажность 52%",
        )

    def test_missing_or_offline_reading_is_unavailable(self) -> None:
        self.assertIn("нет данных", self.provider.format_reading("2", None))
        row = SimpleNamespace(
            temperature_c=24.0,
            humidity_percent=50,
            online=False,
        )
        self.assertIn("нет данных", self.provider.format_reading("2", row))

    def test_rejects_unsafe_table_name(self) -> None:
        with self.assertRaises(ValueError):
            self.provider.safe_table_name("readings`; DROP TABLE x")


if __name__ == "__main__":
    unittest.main()
