# TG Server Control

Отдельный Telegram-бот для статусов и управления сервисами домашнего сервера.
Он не является частью `egg_cam`: мониторинг яиц — лишь один из подключённых
status-провайдеров.

## Расширение статуса

Общий `/status` запускает по имени все исполняемые файлы из
`/etc/tg-server-control/status.d`. Каждый provider печатает одну короткую строку:

```text
⏹ Яйца
✅ VPN: AdGuard
✅ Румянцево(SSTP)
❌ Колодец
✅ Температура дома: 22.5 °C
```

Чтобы добавить показатель, положите исполняемый файл `NN-name` в `status.d`.
Префикс `NN` задаёт порядок. Provider должен самостоятельно обработать ошибку и
напечатать строку с подходящим значком. Шаблон находится в
`status-provider.example`.

## Конфигурация

- `/etc/tg-server-control/bot.env` — Telegram token, список администраторов и
  путь к offset; файл не хранится в Git;
- `/etc/tg-server-control/well.env` — настройки проверки данных колодца;
- `/etc/tg-server-control/status.d` — установленные status-провайдеры;
- `/var/lib/tg-server-control/update_offset` — последний обработанный update.

Исходящий Telegram-трафик использует общий SOCKS
`socks5h://127.0.0.1:1079`, предоставляемый `tg-vpn-failover`.

## Установка

```bash
sudo ./install.sh
sudo systemctl enable --now tg-server-control.service
```

Перед первым запуском нужно создать `bot.env` с правами `0600` и при миграции
скопировать текущий offset. Установщик намеренно не создаёт секретный файл.

## Проверка

```bash
sudo /usr/local/sbin/tg-server-control status
sudo /usr/local/sbin/tg-server-control network-status
systemctl status tg-server-control.service --no-pager
python -m unittest discover -s tests
```

