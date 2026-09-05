from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

with patch.dict("sys.modules", {"requests": Mock()}):
    import tg_server_control.bot as bot_module
    from tg_server_control.bot import (
        COMMANDS,
        ControlBot,
        command_keyboard,
        network_keyboard,
        parse_admin_user_ids,
        rumyantsevo_keyboard,
        rumyantsevo_status_text,
        telegram_command_menu,
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
            "⚠️ Дом, 1 этаж: нет данных\n"
            "⚠️ Дом, 2 этаж: нет данных",
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
            side_effect=[
                Mock(
                    ok=True,
                    output=(
                        "🌡 Дом, 1 этаж: 22.5 °C · влажность 51%\n"
                        "🌡 Дом, 2 этаж: 23.0 °C · влажность 49%"
                    ),
                ),
                Mock(ok=True, output="💧 Уровень воды в колодце: 123 см"),
            ]
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

        self.assertEqual(
            helper_runner.call_args_list,
            [unittest.mock.call("nest-climate-status"), unittest.mock.call("well-level")],
        )
        bot.send.assert_called_once_with(
            123,
            rumyantsevo_status_text(
                "🌡 Дом, 1 этаж: 22.5 °C · влажность 51%\n"
                "🌡 Дом, 2 этаж: 23.0 °C · влажность 49%",
                "💧 Уровень воды в колодце: 123 см",
            ),
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

    def test_network_keyboard_has_current_actions(self) -> None:
        callbacks = {
            button["callback_data"]
            for row in network_keyboard()["inline_keyboard"]
            for button in row
        }
        self.assertEqual(
            callbacks,
            {"/vpn_switch", "/sstp_restart", "/network_status", "/status"},
        )

    def test_telegram_menu_covers_commands_except_start(self) -> None:
        menu_commands = {f"/{item['command']}" for item in telegram_command_menu()}
        self.assertEqual(
            menu_commands,
            set(COMMANDS) - {"/start", "/adguard_restart"},
        )

    def test_vpn_switch_returns_to_network_screen(self) -> None:
        helper_runner = Mock(
            side_effect=[
                Mock(ok=True, output="✅ VPN: AdGuard"),
                Mock(
                    ok=True,
                    output="✅ VPN: AdGuard\n✅ MTProto\n✅ Failover",
                ),
            ]
        )
        bot = ControlBot("token", {123}, helper_runner=helper_runner)
        bot.send = Mock()

        bot.handle_update(
            {
                "message": {
                    "from": {"id": 123},
                    "chat": {"id": 123, "type": "private"},
                    "text": "/vpn_switch",
                }
            }
        )

        self.assertEqual(
            helper_runner.call_args_list,
            [
                unittest.mock.call("vpn-switch"),
                unittest.mock.call("network-status"),
            ],
        )
        bot.send.assert_called_with(
            123,
            "✅ VPN: переключение\n\n"
            "✅ VPN: AdGuard\n✅ MTProto\n✅ Failover",
            keyboard=False,
            reply_markup=network_keyboard(),
        )

    def test_bot_synchronizes_telegram_commands_before_polling(self) -> None:
        bot = ControlBot("token", {123})
        bot.api = Mock(side_effect=[None, KeyboardInterrupt])

        class RequestException(Exception):
            pass

        with patch.object(
            bot_module,
            "requests",
            SimpleNamespace(RequestException=RequestException),
        ):
            with self.assertRaises(KeyboardInterrupt):
                bot.run_forever()

        self.assertEqual(
            bot.api.call_args_list[0],
            unittest.mock.call(
                "setMyCommands",
                {"commands": telegram_command_menu()},
            ),
        )


if __name__ == "__main__":
    unittest.main()
