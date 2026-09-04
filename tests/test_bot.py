from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

with patch.dict("sys.modules", {"requests": Mock()}):
    from tg_server_control.bot import (
        command_keyboard,
        parse_admin_user_ids,
        water_report_keyboard,
    )


class BotConfigurationTest(unittest.TestCase):
    def test_parse_admin_ids(self) -> None:
        self.assertEqual(parse_admin_user_ids("1, 2"), {1, 2})

    def test_main_keyboard_has_status_and_well_reports(self) -> None:
        callbacks = {
            button["callback_data"]
            for row in command_keyboard()["inline_keyboard"]
            for button in row
        }
        self.assertIn("/status", callbacks)
        self.assertIn("/water_status", callbacks)

    def test_water_keyboard_has_schedule_toggles(self) -> None:
        callbacks = {
            button["callback_data"]
            for row in water_report_keyboard()["inline_keyboard"]
            for button in row
        }
        self.assertIn("/water_daily_toggle", callbacks)
        self.assertIn("/water_weekly_toggle", callbacks)


if __name__ == "__main__":
    unittest.main()
