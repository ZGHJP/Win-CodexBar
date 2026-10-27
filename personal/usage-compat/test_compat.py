import json
import unittest
import contextlib
import pathlib
import tempfile
import itertools
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
