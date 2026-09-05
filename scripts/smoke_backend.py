#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_message(proc: subprocess.Popen, deadline: float):
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"backend exited early with code {proc.returncode}\n{stderr}")
        if not proc.stdout:
            raise RuntimeError("backend stdout is unavailable")
        ready, _, _ = select.select([proc.stdout], [], [], 0.2)
        if not ready:
            continue
        line = proc.stdout.readline()
        if not line:
            continue
        return json.loads(line)
    raise TimeoutError("backend startup timeout")


def main() -> int:
    env = os.environ.copy()
    env.setdefault("HANDEYE_MOCK", "1")
    env.setdefault("HANDEYE_DATA_DIR", str(ROOT / ".install-smoke"))
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "backend" / "bridge.py")],
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        deadline = time.monotonic() + 12
        while True:
            message = read_message(proc, deadline)
            if message.get("kind") == "event" and message.get("event") == "ready":
                break

        if not proc.stdin:
            raise RuntimeError("backend stdin is unavailable")
        proc.stdin.write(json.dumps({"id": 1, "method": "ping", "params": {}}) + "\n")
        proc.stdin.flush()

        while True:
            message = read_message(proc, time.monotonic() + 5)
            if message.get("kind") == "response" and message.get("id") == 1:
                if not message.get("ok") or not message.get("result", {}).get("pong"):
                    raise RuntimeError(f"backend ping failed: {message}")
                break

        proc.stdin.write(json.dumps({"id": 2, "method": "shutdown", "params": {}}) + "\n")
        proc.stdin.flush()
        proc.stdin.close()
        proc.wait(timeout=5)
        if proc.returncode != 0:
            stderr = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"backend shutdown failed with code {proc.returncode}\n{stderr}")
        print("[HandEye] backend smoke PASS")
        return 0
    except Exception as exc:
        stderr = ""
        if proc.stderr:
            try:
                stderr = proc.stderr.read()
            except Exception:
                stderr = ""
        print(f"[HandEye] backend smoke FAIL: {exc}", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        return 1
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
