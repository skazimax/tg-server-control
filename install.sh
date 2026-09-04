#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "run as root" >&2
    exit 1
fi

repo_dir=$(cd "$(dirname "$0")" && pwd)
install -d -o root -g root -m 0755 /etc/tg-server-control/status.d
install -d -o root -g root -m 0755 /usr/local/lib/tg-server-control
install -d -o skazimax -g skazimax -m 0750 /var/lib/tg-server-control

python3 -m venv "$repo_dir/.venv"
"$repo_dir/.venv/bin/pip" install -q -r "$repo_dir/requirements.txt"

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
install -o root -g root -m 0600 "$repo_dir/config/well.env" \
    /etc/tg-server-control/well.env
install -o root -g root -m 0440 "$repo_dir/systemd/tg-server-control.sudoers" \
    /etc/sudoers.d/tg-server-control
visudo -cf /etc/sudoers.d/tg-server-control >/dev/null
install -o root -g root -m 0644 "$repo_dir/systemd/tg-server-control.service" \
    /etc/systemd/system/tg-server-control.service
systemctl daemon-reload
