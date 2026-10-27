"""Read-only Codex usage projection for CodexBar 0.70's pre-pagination scanner."""
from __future__ import annotations
import argparse
import contextlib
import ctypes
import datetime as dt
import hashlib
import json
import io
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import winreg

BASE = Path(__file__).resolve().parent
NATIVE = Path.home() / ".codex"
VIEW = BASE / "home"
SESSIONS = VIEW / "sessions"
APP = Path(os.environ["LOCALAPPDATA"]) / "Programs/CodexBar/codexbar-desktop.exe"
META_KEYS = ("id", "session_id", "timestamp", "cwd", "forked_from_id", "history_base", "history_mode", "multi_agent_version", "thread_source", "subagent_history_start_ordinal", "source")
TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")

@contextlib.contextmanager
def open_usage(path):
    with path.open("rb") as raw:
        if path.suffix == ".zst":
            sys.path.insert(0, str(BASE / "python-libs"))
            import zstandard
            with zstandard.ZstdDecompressor().stream_reader(raw) as decoded:
                yield io.BufferedReader(decoded)
        else:
            yield raw

def own_usage_lines(meta, events):
    """Convert inherited counters to this conversation's observed request usage."""
    independent = {"id": meta["id"], "timestamp": meta.get("timestamp"), "source": "cli"}
    if meta.get("cwd"):
        independent["cwd"] = meta["cwd"]
    yield json.dumps({"timestamp": meta.get("timestamp"), "type": "session_meta", "payload": independent}, separators=(",", ":"))
    cumulative = {k: 0 for k in TOKEN_KEYS}
    previous = None
    snapshots = set()
    lines = set()
    for stamp, kind, body in events:
        if body in lines:
            continue
        lines.add(body)
        if not kind:
            yield body
            continue
        if meta.get("forked_from_id") and stamp < meta.get("timestamp", ""):
            continue
        row = json.loads(body)
        info = row["payload"]["info"]
        total = info.get("total_token_usage")
        last = info.get("last_token_usage")
        if not isinstance(total, dict) or not isinstance(last, dict):
            continue
        signature = tuple(total.get(k, 0) for k in TOKEN_KEYS)
        if signature in snapshots:
            continue
        snapshots.add(signature)
        if previous is None or any(total.get(k, 0) < previous.get(k, 0) for k in TOKEN_KEYS):
            delta = {k: last.get(k, 0) for k in TOKEN_KEYS}
        else:
            delta = {k: total.get(k, 0) - previous.get(k, 0) for k in TOKEN_KEYS}
        previous = total
        for key in TOKEN_KEYS:
            cumulative[key] += delta[key]
        info["total_token_usage"] = dict(cumulative)
        info["last_token_usage"] = delta
        yield json.dumps(row, separators=(",", ":"))

def atomic_write(path, data):
    if path.exists() and path.read_bytes() == data:
        return False
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)
    return True

def project():
    SESSIONS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(BASE / "usage.sqlite")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, size INTEGER, stamp INTEGER, position INTEGER, metadata TEXT);
        CREATE TABLE IF NOT EXISTS events(path TEXT, offset INTEGER, stamp TEXT, kind INTEGER, body TEXT, PRIMARY KEY(path,offset));
        CREATE INDEX IF NOT EXISTS event_path ON events(path);
    """)
    version = BASE / "projection-version"
    force = not version.exists() or version.read_text() != "4"
    changed = set()
    present = set()
    files_read = 0
    known = {row[0] for row in conn.execute("SELECT path FROM files")}
    if (BASE / "extra-sources.json").exists():
        known.update(json.loads((BASE / "extra-sources.json").read_text()))
    since = (dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date() - dt.timedelta(days=7)).isoformat()
    for root in (NATIVE / "sessions", NATIVE / "archived_sessions"):
        if not root.exists():
            continue
        candidates = list(root.rglob("*.jsonl"))
        for compressed in root.rglob("*.jsonl.zst"):
            native = compressed.with_suffix("")
            dated = re.match(r"rollout-(\d{4}-\d{2}-\d{2})T", compressed.name)
            if not native.exists() and (str(native) in known or str(compressed) in known or (dated and dated.group(1) >= since)):
                candidates.append(compressed)
        for path in candidates:
            key = str(path)
            present.add(key)
            stat = path.stat()
            cached = conn.execute("SELECT size,stamp,position,metadata FROM files WHERE path=?", (key,)).fetchone()
            if cached and cached[0] == stat.st_size and cached[1] == stat.st_mtime_ns and not force:
                continue
            files_read += 1
            if cached:
                old_meta = json.loads(cached[3])
                changed.add(old_meta["id"])
            offset = cached[2] if cached and not force and path.suffix != ".zst" and stat.st_size > cached[0] else 0
            meta = json.loads(cached[3]) if cached and not force else None
            if not offset:
                conn.execute("DELETE FROM events WHERE path=?", (key,))
            with open_usage(path) as stream:
                if offset:
                    stream.seek(offset)
                while True:
                    offset = stream.tell()
                    line = stream.readline()
                    if not line:
                        break
                    if not line.endswith(b"\n") and path.suffix != ".zst":
                        stream.seek(offset)
                        break
                    if not any(marker in line for marker in (b'"session_meta"', b'"turn_context"', b'"token_count"', b'"task_started"')):
                        continue
                    try:
                        obj = json.loads(line)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    payload = obj.get("payload", {})
                    if not isinstance(payload, dict):
                        continue
                    if obj.get("type") == "session_meta" and meta is None:
                        meta = {k: payload[k] for k in META_KEYS if k in payload}
                        # Persist only usage metadata; discard instructions and account identity.
                        if isinstance(meta.get("source"), dict):
                            meta["source"] = "vscode"
                    elif obj.get("type") == "turn_context" and payload.get("model"):
                        body = {"timestamp": obj.get("timestamp"), "type": "turn_context", "payload": {k: payload[k] for k in ("model", "service_tier", "speed", "turn_id") if k in payload}}
                        conn.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?)", (key, offset, obj.get("timestamp", ""), 0, json.dumps(body, separators=(",", ":"))))
                    elif obj.get("type") == "event_msg" and payload.get("type") == "task_started":
                        body = {"timestamp": obj.get("timestamp"), "type": "event_msg", "payload": {k: payload[k] for k in ("type", "turn_id", "id") if k in payload}}
                        conn.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?)", (key, offset, obj.get("timestamp", ""), 0, json.dumps(body, separators=(",", ":"))))
                    elif obj.get("type") == "event_msg" and payload.get("type") == "token_count" and payload.get("info"):
                        body = {"timestamp": obj.get("timestamp"), "type": "event_msg", "payload": {k: payload[k] for k in ("type", "info", "turn_id") if k in payload}}
                        conn.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?)", (key, offset, obj.get("timestamp", ""), 1, json.dumps(body, separators=(",", ":"))))
                position = stream.tell()
            if meta and meta.get("id"):
                changed.add(meta["id"])
                conn.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?)", (key, stat.st_size, stat.st_mtime_ns, position, json.dumps(meta)))
    for key, raw in conn.execute("SELECT path,metadata FROM files").fetchall():
        if key not in present:
            changed.add(json.loads(raw)["id"])
            conn.execute("DELETE FROM events WHERE path=?", (key,))
            conn.execute("DELETE FROM files WHERE path=?", (key,))
    groups = {}
    for key, raw in conn.execute("SELECT path,metadata FROM files"):
        meta = json.loads(raw)
        groups.setdefault(meta["id"], []).append((key, meta))
    if force:
        changed.update(groups)
    written = 0
    for sid in changed:
        target = SESSIONS / ("usage-" + sid + ".jsonl")
        group = sorted(groups.get(sid, []), key=lambda item: item[1].get("timestamp", ""))
        if not group:
            if target.exists():
                target.unlink()
            continue
        # A logical conversation has one authoritative metadata owner. Pagination
        # fragments keep that ID, and their cumulative token records belong to it.
        meta = group[0][1]
        events = []
        for key, _ in group:
            events.extend(conn.execute("SELECT stamp,kind,body FROM events WHERE path=?", (key,)))
        events.sort(key=lambda row: (row[0], row[1]))
        lines = list(own_usage_lines(meta, events))
        written += atomic_write(target, ("\n".join(lines) + "\n").encode())
    conn.commit()
    conn.close()
    version.write_text("4")
    result = {"at": dt.datetime.now(dt.timezone.utc).isoformat(), "sourceFiles": len(present), "conversations": len(groups), "filesRead": files_read, "updatedConversations": written}
    atomic_write(BASE / "status.json", json.dumps(result, indent=2).encode())
    return result

def share_readonly_sources():
    # CodexBar's OAuth reader never refreshes/writes auth.json. Hard links keep
    # the existing protected credential and database in place without copies.
    for name in ("auth.json", "config.toml", "logs_2.sqlite", "logs_2.sqlite-wal", "logs_2.sqlite-shm", "state_5.sqlite", "state_5.sqlite-wal", "state_5.sqlite-shm", "session_index.jsonl"):
        source, target = NATIVE / name, VIEW / name
        if not source.exists():
            if target.exists():
                target.unlink()
            continue
        try:
            if target.exists() and os.path.samefile(source, target):
                continue
            if target.exists():
                target.unlink()
            os.link(source, target)
        except OSError:
            if name in ("auth.json", "config.toml"):
                raise
    # Keep the existing startup preference routed through its compatibility
    # entry point if the desktop shell rewrites it to its runtime alias.
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
            value, kind = winreg.QueryValueEx(key, "CodexBar")
            if "codexbar-desktop.exe" in value.lower():
                winreg.SetValueEx(key, "CodexBar", 0, kind, '"' + str(APP.with_name("codexbar.exe")) + '"')
    except FileNotFoundError:
        pass

def refresh_indexes():
    """The Daily spend chart reads its own durable snapshot, not cost totals."""
    if (BASE / "native-pr779.enabled").is_file():
        atomic_write(BASE / "index-status.json", json.dumps({
            "at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "managedBy": "native-pr779",
            "externalForceRefresh": False,
        }).encode())
        return
    windows = {7, 30}
    sidecar = BASE.parent / "local-usage/codex-workspaces-v1.sqlite"
    if sidecar.exists():
        with sqlite3.connect(sidecar) as conn:
            windows.update(row[0] for row in conn.execute("SELECT DISTINCT history_days FROM snapshot_payloads"))
    env = dict(os.environ, CODEX_HOME=str(VIEW))
    for days in sorted(day for day in windows if 1 <= day <= 365):
        subprocess.run([str(APP.with_name("codexbar-cli.exe")), "workspaces", "--days", str(days), "--force", "--json"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    atomic_write(BASE / "index-status.json", json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(), "historyDays": sorted(windows)}).encode())

def launch():
    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.restype = ctypes.c_void_p
    mutex = kernel.CreateMutexW(None, False, "Local\\CodexBarUsageCompatibility-JP")
    already_running = kernel.GetLastError() == 183
    env = dict(os.environ, CODEX_HOME=str(VIEW))
    if already_running:
        subprocess.Popen([str(APP)], env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        return
    try:
        project()
        share_readonly_sources()
        refresh_indexes()
        child = subprocess.Popen([str(APP)], env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        last_index = time.monotonic()
        last_desktop = time.monotonic()
        while True:
            now = time.monotonic()
            child_alive = child is not None and child.poll() is None
            if not child_alive:
                # Release Popen's Windows process handle after handoff. Keeping
                # a terminated process object can keep its executable in use.
                child = None
            if child_alive or desktop_is_running():
                last_desktop = now
            elif now - last_desktop >= 30:
                # Real Quit ends the companion too. Native restarts can hand
                # off to another PID, with a short gap between processes.
                break
            time.sleep(15)
            try:
                result = project()
                share_readonly_sources()
                if result["updatedConversations"] or time.monotonic() - last_index >= 300:
                    refresh_indexes()
                    last_index = time.monotonic()
            except Exception as error:
                with (BASE / "errors.log").open("a", encoding="utf-8") as log:
                    log.write(type(error).__name__ + ": " + str(error) + "\n")
    finally:
        kernel.CloseHandle(ctypes.c_void_p(mutex))


def desktop_is_running():
    """Match the actual executable path, not the original launcher child PID."""
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    psapi.EnumProcesses.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    psapi.EnumProcesses.restype = wintypes.BOOL
    processes = (wintypes.DWORD * 8192)()
    size = wintypes.DWORD()
    if not psapi.EnumProcesses(processes, ctypes.sizeof(processes), ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    expected = os.path.normcase(os.path.abspath(APP))
    for pid in processes[:size.value // ctypes.sizeof(wintypes.DWORD)]:
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            continue
        try:
            path = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(path))
            if kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(length)):
                if os.path.normcase(os.path.abspath(path.value)) == expected:
                    return True
        finally:
            kernel.CloseHandle(handle)
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    if args.launch:
        launch()
    else:
        print(json.dumps(project()))
