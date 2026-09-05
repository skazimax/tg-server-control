import os
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ShellStatusTest(unittest.TestCase):
    def job(self, active='inactive', result='success', started='0'):
        script='''systemctl() {
if [[ "$1" == is-active ]]; then echo "$ACTIVE";
elif [[ "$4" == Result ]]; then echo "$RESULT";
else echo "$STARTED"; fi
}
source "$STATUS_LIB"
unit_icon report report.service job
'''
        env=dict(os.environ,ACTIVE=active,RESULT=result,STARTED=started,STATUS_LIB=str(ROOT/'lib/status-common.sh'))
        return subprocess.check_output(['bash','-c',script],env=env,text=True)
    def test_never_run_not_success(self):
        self.assertTrue(self.job().startswith('⚪'))
    def test_completed_success(self):
        self.assertTrue(self.job(started='123').startswith('✅'))
    def test_completed_error(self):
        self.assertTrue(self.job(result='exit-code',started='123').startswith('❌'))
    def test_running_not_completed(self):
        self.assertTrue(self.job(active='activating',started='123').startswith('⏳'))
    def test_camera_default_route_not_accepted(self):
        text=(ROOT/'scripts/tg-server-control').read_text()
        function=text[text.index('network_status() {'):text.index('\ncase "${1:-}"')]
        script='''run_status_provider() { :; }
ip() { echo "192.168.2.3 dev $DEVICE src 192.0.2.1"; }
status_dir=/nonexistent
'''+function.replace('[[ -x /usr/local/sbin/tg-vpn-failover-status ]]','[[ -x /nonexistent ]]')+'\nnetwork_status\n'
        for device,icon in [('eth0','❌'),('ppp20','✅')]:
            out=subprocess.check_output(['bash','-c',script],env=dict(os.environ,DEVICE=device),text=True)
            self.assertTrue(out.startswith(icon),out)
