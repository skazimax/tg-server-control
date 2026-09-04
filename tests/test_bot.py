from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

with patch.dict("sys.modules", {"requests": Mock()}):
    from tg_server_control.bot import (
        ControlBot,
        command_keyboard,
        parse_admin_user_ids,
        rumyantsevo_keyboard,
        rumyantsevo_status_text,
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
        self.assertIn("/rumyantsevo", callbacks)

    def test_rumyantsevo_screen_has_all_placeholder_statuses(self) -> None:
        text = rumyantsevo_status_text(
            "⚠️ Уровень воды в колодце: нет данных"
        )
        self.assertIn("Дом, 1 этаж: нет данных", text)
        self.assertIn("Дом, 2 этаж: нет данных", text)
        self.assertIn("Улица: нет данных", text)
        self.assertIn("Колодец: нет данных", text)
        self.assertIn("⚠️ Уровень воды в колодце: нет данных", text)

    def test_rumyantsevo_keyboard_has_refresh_and_back(self) -> None:
        callbacks = {
            button["callback_data"]
            for row in rumyantsevo_keyboard()["inline_keyboard"]
            for button in row
        }
        self.assertEqual(callbacks, {"/rumyantsevo", "/status"})

    def test_rumyantsevo_screen_uses_real_well_level(self) -> None:
        helper_runner = Mock(
            return_value=Mock(
                ok=True,
                output="💧 Уровень воды в колодце: 123 см",
            )
        )
        bot = ControlBot("token", {123}, helper_runner=helper_runner)
        bot.send = Mock()

        bot.handle_update(
            {
                "message": {
                    "from": {"id": 123},
                    "chat": {"id": 123, "type": "private"},
                    "text": "/rumyantsevo",
                }
            }
        )

        helper_runner.assert_called_once_with("well-level")
        bot.send.assert_called_once_with(
            123,
            rumyantsevo_status_text("💧 Уровень воды в колодце: 123 см"),
            reply_markup=rumyantsevo_keyboard(),
        )

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
