#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "run as root" >&2
    exit 1
fi

repo_dir=$(cd "$(dirname "$0")" && pwd)
app_root=/opt/tg-server-control
service_user=tg-server-control
if systemctl is-active --quiet tg-server-control.service && \
    [[ $(systemctl show tg-server-control.service -p User --value) != "$service_user" ]]; then
    echo "stop tg-server-control.service before migrating its user; preserve the live offset" >&2
    exit 1
fi
if ! id "$service_user" >/dev/null 2>&1; then
    useradd --system --user-group --home-dir /var/lib/tg-server-control \
        --no-create-home --shell /usr/sbin/nologin "$service_user"
fi
install -d -o root -g root -m 0700 /etc/tg-server-control
install -d -o root -g root -m 0755 /etc/tg-server-control/status.d
install -d -o root -g root -m 0755 /usr/local/lib/tg-server-control
install -d -o "$service_user" -g "$service_user" -m 0750 /var/lib/tg-server-control
if [[ -f /var/lib/tg-server-control/update_offset ]]; then
    chown "$service_user:$service_user" /var/lib/tg-server-control/update_offset
    chmod 0600 /var/lib/tg-server-control/update_offset
fi
install -d -o root -g root -m 0755 "$app_root" "$app_root/app" \
    "$app_root/app/tg_server_control"
install -o root -g root -m 0644 "$repo_dir/tg_server_control/"*.py \
    "$app_root/app/tg_server_control/"
install -o root -g root -m 0644 "$repo_dir/requirements.txt" "$app_root/requirements.txt"

if [[ ${TG_CONTROL_SKIP_DEPS:-0} != 1 ]]; then
    python3 -m venv "$app_root/venv"
    "$app_root/venv/bin/python" -m pip install -q -r "$app_root/requirements.txt"
fi
"$app_root/venv/bin/python" -I -c 'import requests, socks, ydb'
chown -R root:root "$app_root"
chmod -R go-w "$app_root"

install -o root -g root -m 0755 "$repo_dir/scripts/tg-server-control" \
    /usr/local/sbin/tg-server-control
install -o root -g root -m 0644 "$repo_dir/lib/status-common.sh" \
    /usr/local/lib/tg-server-control/status-common.sh
install -o root -g root -m 0644 "$repo_dir/providers/well_status.py" \
    /usr/local/lib/tg-server-control/well_status.py
install -o root -g root -m 0644 "$repo_dir/providers/nest_temperature.py" \
    /usr/local/lib/tg-server-control/nest_temperature.py
install -o root -g root -m 0644 "$repo_dir/providers/nest_climate_status.py" \
    /usr/local/lib/tg-server-control/nest_climate_status.py
install -o root -g root -m 0755 "$repo_dir/status.d/"* \
    /etc/tg-server-control/status.d/
if [[ ! -e /etc/tg-server-control/well.env ]]; then
    install -o root -g root -m 0600 "$repo_dir/config/well.env" \
        /etc/tg-server-control/well.env
fi
# Copy only the YDB credential data, preserving the report service's source key.
python3 - <<'PY'
import os
import shlex
import shutil
from pathlib import Path

config = Path('/etc/tg-server-control/well.env')
key_name = 'YDB_SERVICE_ACCOUNT_KEY_FILE_CREDENTIALS'
destination = Path('/etc/tg-server-control/ydb-sa-key.json')
lines = config.read_text().splitlines()
for index, line in enumerate(lines):
    if not line.startswith(key_name + '='):
        continue
    values = shlex.split(line.split('=', 1)[1])
    if not values:
        raise SystemExit('YDB credential path is empty')
    source = Path(values[0])
    if source != destination:
        if not source.is_file():
            raise SystemExit('YDB credential file is missing')
        # Create with restrictive permissions from the first write.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as output, source.open('rb') as input_file:
            shutil.copyfileobj(input_file, output)
        destination.chmod(0o600)
        os.chown(destination, 0, 0)
        lines[index] = key_name + '=' + shlex.quote(str(destination))
    elif not destination.is_file():
        raise SystemExit('Create /etc/tg-server-control/ydb-sa-key.json before installation')
config.write_text('\n'.join(lines) + '\n')
config.chmod(0o600)
PY
visudo -cf "$repo_dir/systemd/tg-server-control.sudoers" >/dev/null
install -o root -g root -m 0440 "$repo_dir/systemd/tg-server-control.sudoers" \
    /etc/sudoers.d/tg-server-control
visudo -cf /etc/sudoers.d/tg-server-control >/dev/null
install -o root -g root -m 0644 "$repo_dir/systemd/tg-server-control.service" \
    /etc/systemd/system/tg-server-control.service
systemctl daemon-reload
