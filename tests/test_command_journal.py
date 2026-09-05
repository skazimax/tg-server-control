import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
with patch.dict('sys.modules', {'requests': Mock()}):
    from tg_server_control.bot import ControlBot, HelperResult, run_helper
from tg_server_control.command_journal import CommandJournal


def update(number=10, text='/vpn_switch', user=123):
    return {'update_id': number, 'message': {'from': {'id': user}, 'chat': {'id': user, 'type': 'private'}, 'text': text}}


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.journal = CommandJournal(self.root / 'commands.sqlite3')
        self.addCleanup(self.journal.db.close)
        self.helper = Mock(return_value=HelperResult(True, 'status'))
        self.bot = ControlBot('secret-token', {123}, self.helper, self.root / 'offset', self.journal)

    def api_updates(self, updates, fail_send=False, fail_ack=False):
        def api(method, payload, **kwargs):
            if method == 'getUpdates': return updates
            if method == 'sendMessage' and fail_send: raise RuntimeError('delivery failure')
            if method == 'answerCallbackQuery' and fail_ack: raise RuntimeError('expired callback')
        self.bot.api = Mock(side_effect=api)

    def row(self):
        return self.journal.db.execute('SELECT execution, delivery FROM commands').fetchone()

    def test_failed_reply_does_not_repeat_command(self):
        self.api_updates([update()], fail_send=True)
        self.bot.poll_once()
        self.assertEqual(self.row(), ('success', 'unknown'))
        self.assertEqual(self.helper.call_count, 2)
        self.bot.poll_once()
        self.assertEqual(self.helper.call_count, 2)
        self.assertEqual((self.root/'offset').read_text(), '11')

    def test_duplicate_after_offset_loss_is_not_executed(self):
        self.journal.claim(10, 123, '/vpn_switch')
        self.api_updates([update()])
        self.bot.poll_once()
        self.helper.assert_not_called()
        self.assertEqual(self.bot.offset, 11)

    def test_restart_marks_interrupted_command_unknown(self):
        self.journal.claim(10, 123, '/vpn_switch')
        second = CommandJournal(self.root / 'commands.sqlite3')
        self.addCleanup(second.db.close)
        self.assertEqual(self.row(), ('unknown', 'pending'))
        self.assertFalse(second.claim(10, 123, '/vpn_switch'))

    def test_cannot_execute_if_receipt_cannot_be_saved(self):
        self.api_updates([update()])
        with patch.object(self.journal, 'claim', side_effect=sqlite3.OperationalError('disk full')):
            with self.assertRaises(sqlite3.OperationalError): self.bot.poll_once()
        self.helper.assert_not_called()
        self.assertIsNone(self.bot.offset)

    def test_cannot_execute_if_offset_cannot_be_saved(self):
        self.api_updates([update()])
        with patch.object(self.bot, '_save_offset', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.bot.poll_once()
        self.helper.assert_not_called()
        self.assertEqual(self.row()[0], 'running')

    def test_error_preserved_when_status_succeeds(self):
        self.helper.side_effect = [HelperResult(False, 'SWITCH FAILED'), HelperResult(True, 'NETWORK OK')]
        self.api_updates([update()]); self.bot.poll_once()
        final = self.bot.api.call_args_list[-1].args[1]['text']
        self.assertIn('SWITCH FAILED', final); self.assertIn('NETWORK OK', final)
        self.assertTrue(final.startswith('❌')); self.assertEqual(self.row(), ('failed', 'sent'))
        events = self.journal.db.execute('SELECT action,result FROM helper_events').fetchall()
        self.assertEqual(events, [('vpn-switch','started'),('vpn-switch','failed'),('network-status','started'),('network-status','success')])

    def test_timeout_remains_unknown_after_good_status(self):
        self.helper.side_effect = [HelperResult(False, 'unknown timeout', True), HelperResult(True, 'NETWORK OK')]
        self.api_updates([update()]); self.bot.poll_once()
        self.assertEqual(self.row(), ('unknown', 'sent'))
        self.assertTrue(self.bot.api.call_args_list[-1].args[1]['text'].startswith('⚠️'))

    def test_expired_callback_does_not_lose_command(self):
        data = {'update_id':10,'callback_query':{'id':'expired','from':{'id':123},'message':{'chat':{'id':123,'type':'private'}},'data':'/vpn_switch'}}
        self.api_updates([data], fail_send=True, fail_ack=True); self.bot.poll_once()
        self.assertEqual(self.helper.call_count,2); self.assertEqual(self.row(), ('success','unknown'))

    def test_corrupt_offset_not_reset(self):
        (self.root/'offset').write_text('bad')
        with self.assertRaises(RuntimeError): ControlBot('token',{123},offset_file=self.root/'offset')

    def test_rejected_command_no_helper_or_raw_text(self):
        self.api_updates([update(text='private arbitrary secret', user=999)]); self.bot.poll_once()
        self.helper.assert_not_called()
        self.assertEqual(self.journal.db.execute('SELECT command FROM commands').fetchone()[0], 'unrecognized')

    def test_empty_message(self):
        self.api_updates([update(text='')]); self.bot.poll_once()
        self.helper.assert_not_called(); self.assertEqual(self.row(), ('ignored','sent'))

    def test_status_header_not_all_healthy(self):
        self.api_updates([update(text='/status')]); self.bot.poll_once()
        self.assertTrue(self.bot.api.call_args_list[-1].args[1]['text'].startswith('ℹ️'))

    def test_prune_preserves_unknown_and_unacknowledged(self):
        for number in [1,2,3]:
            self.journal.claim(number,123,'/status')
            self.journal.finish(number,'unknown' if number==2 else 'success','sent')
        with self.journal.db: self.journal.db.execute('UPDATE commands SET updated_at=0')
        self.journal.prune(3)
        self.assertEqual(self.journal.db.execute('SELECT update_id FROM commands ORDER BY update_id').fetchall(),[(2,),(3,)])

    def test_timeout_helper_result_uncertain(self):
        import subprocess
        with patch('tg_server_control.bot.subprocess.run',side_effect=subprocess.TimeoutExpired('helper',180)):
            result=run_helper('vpn-switch')
        self.assertFalse(result.ok); self.assertTrue(result.uncertain)
