import json
import unittest
import contextlib
import pathlib
import tempfile
import itertools
import datetime as dt
import sqlite3
import sys
from unittest.mock import patch
import compat
from unittest.mock import MagicMock
from compat import own_usage_lines

def event(stamp, total, last):
    body = {"timestamp": stamp, "type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": total, "total_tokens": total}, "last_token_usage": {"input_tokens": last, "total_tokens": last}}}}
    return stamp, 1, json.dumps(body)

class OwnUsageTest(unittest.TestCase):
    def test_migration_removes_store_redirected_links_and_updates_old_helper(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            native, active, legacy = base / 'native', base / 'active/home', base / 'store-cache/home'
            native.mkdir(); active.mkdir(parents=True); legacy.mkdir(parents=True)
            old_script = legacy.parent / 'compat.py'
            old_script.write_bytes(b'# CodexBarUsageCompatibility-JP legacy fixture')
            for name in ('auth.json', 'state_5.sqlite', 'logs_2.sqlite'):
                (native / name).write_bytes(b'synthetic original')
                (legacy / name).hardlink_to(native / name)
            with patch.multiple(compat, NATIVE=native, VIEW=active), patch.object(compat, 'known_projection_homes', return_value={active, legacy}):
                compat.migrate_legacy_homes()
            self.assertEqual((native / 'auth.json').stat().st_nlink, 1)
            self.assertEqual((native / 'auth.json').read_bytes(), b'synthetic original')
            self.assertFalse((legacy / 'auth.json').exists())
            self.assertNotIn(b'os.link(', old_script.read_bytes())

    def test_credentials_never_share_file_identity_and_follow_atomic_login(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            native, view = base / 'native', base / 'view'
            native.mkdir(); view.mkdir()
            for name in ('auth.json', 'config.toml'):
                (native / name).write_bytes(b'synthetic-before-login')
                (view / name).hardlink_to(native / name)
            with patch.multiple(compat, NATIVE=native, VIEW=view), patch.object(compat.winreg, 'OpenKey', side_effect=FileNotFoundError):
                compat.share_readonly_sources()
                for name in ('auth.json', 'config.toml'):
                    self.assertEqual((native / name).stat().st_nlink, 1, 'Codex must be able to persist credentials')
                    self.assertFalse((native / name).samefile(view / name))
                replacement = native / 'new-auth'
                replacement.write_bytes(b'synthetic-after-login')
                replacement.replace(native / 'auth.json')
                compat.share_readonly_sources()
                self.assertEqual((view / 'auth.json').read_bytes(), b'synthetic-after-login')
                self.assertEqual((native / 'auth.json').stat().st_nlink, 1)
                (native / 'auth.json').unlink()
                compat.share_readonly_sources()
                self.assertFalse((view / 'auth.json').exists(), 'logout must remove stale credential copies')

    def test_trace_snapshot_includes_committed_wal_without_sharing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            native, view = base / 'native', base / 'view'
            native.mkdir(); view.mkdir()
            source = native / 'logs_2.sqlite'
            with contextlib.closing(sqlite3.connect(source)) as conn:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA wal_autocheckpoint=0')
                conn.execute('CREATE TABLE proof(value TEXT)')
                conn.execute("INSERT INTO proof VALUES ('committed in WAL')")
                conn.commit()
                for suffix in ('', '-wal', '-shm'):
                    (view / ('logs_2.sqlite' + suffix)).hardlink_to(native / ('logs_2.sqlite' + suffix))
                with patch.multiple(compat, NATIVE=native, VIEW=view), patch.object(compat.winreg, 'OpenKey', side_effect=FileNotFoundError):
                    compat.share_readonly_sources()
                self.assertEqual(source.stat().st_nlink, 1)
                self.assertFalse(source.samefile(view / 'logs_2.sqlite'))
                self.assertFalse((view / 'logs_2.sqlite-wal').exists())
                with contextlib.closing(sqlite3.connect(view / 'logs_2.sqlite')) as snapshot:
                    self.assertEqual(snapshot.execute('SELECT value FROM proof').fetchone()[0], 'committed in WAL')
                conn.execute("INSERT INTO proof VALUES ('later WAL row')")
                conn.commit()
                later = max(compat._trace_snapshot.values()) + 301
                with patch.multiple(compat, NATIVE=native, VIEW=view), patch.object(compat.time, 'monotonic', return_value=later):
                    compat.sync_trace_snapshot()
                with contextlib.closing(sqlite3.connect(view / 'logs_2.sqlite')) as snapshot:
                    self.assertEqual(snapshot.execute('SELECT count(*) FROM proof').fetchone()[0], 2)

    def test_failed_credential_copy_keeps_original_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            source, target = base / 'native-auth', base / 'view-auth'
            source.write_bytes(b'synthetic-token')
            target.hardlink_to(source)
            identity = source.stat().st_ino
            with patch.object(compat.os, 'replace', side_effect=PermissionError('synthetic open handle')):
                with self.assertRaises(PermissionError):
                    compat.sync_independent_file(source, target)
            self.assertEqual(source.stat().st_ino, identity)
            self.assertEqual(source.read_bytes(), b'synthetic-token')
            self.assertTrue(source.samefile(target))
            self.assertEqual(list(base.glob('*.tmp')), [])
            compat.sync_independent_file(source, target)
            self.assertEqual(source.stat().st_nlink, 1)

    def test_first_install_includes_compressed_history_older_than_one_week(self):
        import zstandard
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            native, view = base / 'native', base / 'view'
            (native / 'sessions').mkdir(parents=True)
            stamp = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=20)).isoformat().replace('+00:00', 'Z')
            metadata = {'timestamp': stamp, 'type': 'session_meta', 'payload': {'id': 'older-compressed', 'timestamp': stamp}}
            content = (json.dumps(metadata) + '\n' + event(stamp, 25, 25)[2] + '\n').encode()
            (native / 'sessions' / ('rollout-' + stamp[:10] + 'T00-00-00-test.jsonl.zst')).write_bytes(zstandard.ZstdCompressor().compress(content))
            with patch.multiple(compat, BASE=base, NATIVE=native, VIEW=view, SESSIONS=view / 'sessions'):
                compat.project()
            self.assertTrue((view / 'sessions/usage-older-compressed.jsonl').exists())

    def test_projection_does_not_link_native_discovery_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            native, view = base / 'native', base / 'view'
            native.mkdir(); view.mkdir()
            for name in ('state_5.sqlite', 'state_5.sqlite-wal', 'state_5.sqlite-shm', 'session_index.jsonl', 'logs_2.sqlite'):
                source = native / name
                source.write_bytes(b'original-catalog')
                (view / name).hardlink_to(source)
            with patch.multiple(compat, NATIVE=native, VIEW=view), patch.object(compat.winreg, 'OpenKey', side_effect=FileNotFoundError):
                compat.share_readonly_sources()
            self.assertFalse((view / 'state_5.sqlite').exists())
            self.assertFalse((view / 'session_index.jsonl').exists())
            self.assertEqual((native / 'logs_2.sqlite').stat().st_nlink, 1)
            self.assertEqual((native / 'state_5.sqlite').read_bytes(), b'original-catalog')

    def test_projection_preserves_fast_turn_join_without_prompt_text(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            native = base / "native"
            (native / "sessions").mkdir(parents=True)
            view = base / "view"
            stamp = "2026-10-26T01:00:00Z"
            records = [
                {"timestamp": stamp, "type": "session_meta", "payload": {"id": "fast-test", "timestamp": stamp}},
                {"timestamp": stamp, "type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-fast", "private": "must not copy"}},
                {"timestamp": stamp, "type": "turn_context", "payload": {"model": "gpt-6-astra", "turn_id": "turn-fast", "service_tier": "priority", "private": "must not copy"}},
                json.loads(event(stamp, 110, 10)[2]),
            ]
            source = native / "sessions/fixture.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in records)+"\n")
            with patch.multiple(compat, BASE=base, NATIVE=native, VIEW=view, SESSIONS=view / "sessions"):
                compat.project()
                text = (view / "sessions/usage-fast-test.jsonl").read_text()
                projected = [json.loads(line) for line in text.splitlines()]
                self.assertTrue(any(row["payload"].get("type") == "task_started" and row["payload"].get("turn_id") == "turn-fast" for row in projected))
                self.assertTrue(any(row.get("type") == "turn_context" and row["payload"].get("turn_id") == "turn-fast" for row in projected))
                self.assertNotIn("must not copy", text)
                # Simulate an older projection schema without changing source
                # size or mtime: upgrade must still re-read retained events.
                (base / "projection-version").write_text("3")
                with contextlib.closing(sqlite3.connect(base / "usage.sqlite")) as conn:
                    conn.execute("DELETE FROM events")
                    conn.commit()
                compat.project()
                self.assertIn('"task_started"', (view / "sessions/usage-fast-test.jsonl").read_text())

    def normalized(self, events, fork=False):
        meta = {"id": "logical", "timestamp": "2026-10-20T00:00:00Z"}
        if fork:
            meta["forked_from_id"] = "parent"
        return [json.loads(line) for line in own_usage_lines(meta, events)]

    def test_inherited_counter_and_republished_snapshot(self):
        rows = self.normalized([event("2026-10-21T01:00:00Z", 110, 10), event("2026-10-21T01:00:01Z", 110, 10), event("2026-10-21T01:00:02Z", 120, 10)], fork=True)
        self.assertNotIn("forked_from_id", rows[0]["payload"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["payload"]["info"]["total_token_usage"]["total_tokens"], 20)

    def test_counter_reset_in_next_fragment(self):
        rows = self.normalized([event("2026-10-21T01:00:00Z", 110, 10), event("2026-10-21T02:00:00Z", 7, 7)])
        self.assertEqual(rows[-1]["payload"]["info"]["total_token_usage"]["total_tokens"], 17)

    def test_copied_history_before_fork_is_not_billed_again(self):
        rows = self.normalized([event("2026-10-19T01:00:00Z", 100, 100), event("2026-10-21T01:00:00Z", 110, 10)], fork=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]["payload"]["info"]["total_token_usage"]["total_tokens"], 10)

    def test_native_log_can_be_compressed_between_refreshes(self):
        sys.path.insert(0, str(compat.BASE / "python-libs"))
        import zstandard
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            native = base / "native"
            (native / "sessions").mkdir(parents=True)
            view = base / "view"
            source = native / "sessions/rollout-2026-10-21T00-00-00-logical.jsonl"
            metadata = {"timestamp": "2026-10-21T00:00:00Z", "type": "session_meta", "payload": {"id": "logical", "timestamp": "2026-10-21T00:00:00Z", "cwd": "C:/project"}}
            data = (json.dumps(metadata) + "\n" + event("2026-10-21T01:00:00Z", 110, 10)[2] + "\n").encode()
            source.write_bytes(data)
            with patch.multiple(compat, BASE=base, NATIVE=native, VIEW=view, SESSIONS=view / "sessions"):
                compat.project()
                target = view / "sessions/usage-logical.jsonl"
                expected = target.read_bytes()
                source.with_suffix(".jsonl.zst").write_bytes(zstandard.ZstdCompressor().compress(data))
                source.unlink()
                compat.project()
                self.assertEqual(target.read_bytes(), expected)
                self.assertEqual(json.loads(target.read_text().splitlines()[0])["payload"]["cwd"], "C:/project")

class NativeFreshnessModeTest(unittest.TestCase):
    def test_public_price_renewal_is_nonblocking_and_rate_limited(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            (base / 'price_catalog.py').touch()
            child = MagicMock()
            child.poll.return_value = None
            with patch.object(compat, 'BASE', base), patch.object(compat.subprocess, 'Popen', return_value=child) as start:
                refresh = compat.PricingRefresh()
                refresh.tick(100)
                refresh.tick(115)
                start.assert_called_once()
                child.wait.assert_not_called()
                child.poll.return_value = 0
                refresh.tick(200)
                start.assert_called_once()
                refresh.tick(1000)
                self.assertEqual(start.call_count, 2)
                refresh.close()

    def test_native_restart_keeps_projection_alive_for_replacement_process(self):
        kernel = MagicMock()
        kernel.CreateMutexW.return_value = 123
        kernel.GetLastError.return_value = 0
        child = MagicMock()
        child.poll.side_effect = [None, 0, 0, 0, 0]
        with patch.object(compat.ctypes.windll, "kernel32", kernel), \
             patch.object(compat.subprocess, "Popen", return_value=child), \
             patch.object(compat, "desktop_is_running", side_effect=[True, False, False], create=True), \
             patch.object(compat.time, "sleep"), \
             patch.object(compat.time, "monotonic", side_effect=itertools.count(0, 15)), \
             patch.object(compat, "project", return_value={"updatedConversations": 0}) as project, \
             patch.object(compat, "share_readonly_sources"), \
             patch.object(compat, "refresh_indexes"):
            compat.launch()
        self.assertEqual(project.call_count, 3, "replacement must keep projection alive, and real Quit must eventually stop it")

    def test_short_native_restart_gap_is_tolerated(self):
        kernel = MagicMock()
        kernel.CreateMutexW.return_value = 123
        kernel.GetLastError.return_value = 0
        child = MagicMock()
        child.poll.side_effect = itertools.chain([None], itertools.repeat(0))
        with patch.object(compat.ctypes.windll, "kernel32", kernel), \
             patch.object(compat.subprocess, "Popen", return_value=child), \
             patch.object(compat, "desktop_is_running", side_effect=[False, True, False, False, False]), \
             patch.object(compat.time, "sleep"), \
             patch.object(compat.time, "monotonic", side_effect=itertools.count(0, 5)), \
             patch.object(compat, "project", return_value={"updatedConversations": 0}) as project, \
             patch.object(compat, "share_readonly_sources"), \
             patch.object(compat, "refresh_indexes"):
            compat.launch()
        self.assertEqual(project.call_count, 6)

    def test_patched_runtime_owns_snapshot_refresh_without_external_force(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp) / "compat"
            base.mkdir()
            (base / "native-pr779.enabled").write_text("enabled")
            with patch.object(compat, "BASE", base), patch.object(compat.subprocess, "run") as run:
                compat.refresh_indexes()
            self.assertEqual(run.call_count, 0)
            status = json.loads((base / "index-status.json").read_text())
            self.assertEqual(status["managedBy"], "native-pr779")
            self.assertFalse(status["externalForceRefresh"])

    def test_unpatched_runtime_retains_legacy_forced_refresh(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp) / "compat"
            base.mkdir()
            with patch.object(compat, "BASE", base), patch.object(compat.subprocess, "run") as run:
                compat.refresh_indexes()
            self.assertEqual(run.call_count, 2)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual({args[args.index("--days") + 1] for args in commands}, {"7", "30"})
            self.assertTrue(all("--force" in args for args in commands))

if __name__ == "__main__":
    unittest.main()
