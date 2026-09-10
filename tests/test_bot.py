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
        status_keyboard,
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
        self.assertEqual(
            callbacks,
            {"/status", "/rumyantsevo", "/reports", "/network"},
        )

    def test_status_keyboard_has_contextual_egg_action(self) -> None:
        stopped = status_keyboard("⏹ Яйца")
        active = status_keyboard("✅ Яйца")
        stopped_callbacks = {
            button["callback_data"] for row in stopped["inline_keyboard"] for button in row
        }
        active_callbacks = {
            button["callback_data"] for row in active["inline_keyboard"] for button in row
        }
        self.assertIn("/egg_on", stopped_callbacks)
        self.assertNotIn("/egg_off", stopped_callbacks)
        self.assertIn("/egg_off", active_callbacks)
        self.assertIn("/egg_restart", active_callbacks)

    def test_rumyantsevo_screen_has_all_placeholder_statuses(self) -> None:
        text = rumyantsevo_status_text(
            "⚠️ 1 этаж: нет данных\n"
            "⚠️ 2 этаж: нет данных",
            "⚠️ Уровень: нет данных"
        )
        self.assertIn("1 этаж: нет данных", text)
        self.assertIn("2 этаж: нет данных", text)
        self.assertIn("Улица: нет данных", text)
        self.assertIn("Колодец: нет данных", text)
        self.assertIn("⚠️ Уровень: нет данных", text)

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
                        "🌡 1 этаж: 22.5 °C · 51%\n"
                        "🌡 2 этаж: 23.0 °C · 49%"
                    ),
                ),
                Mock(ok=True, output="💧 Уровень: 123 см"),
            ]
        )
        bot = ControlBot("token", {123}, helper_runner=helper_runner)
        bot.send = Mock(return_value=None)

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
                "🌡 1 этаж: 22.5 °C · 51%\n"
                "🌡 2 этаж: 23.0 °C · 49%",
                "💧 Уровень: 123 см",
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
        self.assertIn("/water_daily", callbacks)
        self.assertIn("/water_weekly", callbacks)
        self.assertIn("/climate_weekly", callbacks)

    def test_network_keyboard_has_current_actions(self) -> None:
        callbacks = {
            button["callback_data"]
            for row in network_keyboard()["inline_keyboard"]
            for button in row
        }
        self.assertEqual(
            callbacks,
            {"/vpn_switch", "/sstp_restart", "/network", "/status"},
        )

    def test_climate_report_runs_helper_and_returns_to_reports_screen(self) -> None:
        report_status = "✅ Колодец · сутки\n✅ Колодец · 7 дней"
        helper_runner = Mock(
            side_effect=[
                Mock(ok=True, output="Отчёт отправлен"),
                Mock(ok=True, output=report_status),
            ]
        )
        bot = ControlBot("token", {123}, helper_runner=helper_runner)
        bot.send = Mock(return_value=None)

        bot.handle_update(
            {
                "message": {
                    "from": {"id": 123},
                    "chat": {"id": 123, "type": "private"},
                    "text": "/climate_weekly",
                }
            }
        )

        self.assertEqual(
            helper_runner.call_args_list,
            [
                unittest.mock.call("climate-weekly"),
                unittest.mock.call("water-status"),
            ],
        )
        bot.send.assert_called_with(
            123,
            "✅ Отчёт отправлен",
            reply_markup=water_report_keyboard(report_status),
        )

    def test_telegram_menu_covers_commands_except_start(self) -> None:
        menu_commands = {f"/{item['command']}" for item in telegram_command_menu()}
        self.assertEqual(menu_commands, {"/status", "/rumyantsevo", "/reports", "/network", "/help"})

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
        bot.send = Mock(return_value=None)

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
            "Сеть\n\n✅ VPN: AdGuard\n✅ MTProto\n✅ Failover",
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
