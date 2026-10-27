#!/usr/bin/env python3
"""
Host side: wait for a detached pod session (runpod_assembly_runner.sh start <params>) to
finish, with short SSH polls instead of one long-lived connection (a silent long connection
was dropped once and left a pod idling). Exits with the session's exit code, 124 on timeout.

Usage: python wait_pod_session.py --host H --port P --params params/<file>.json
       [--poll 20] [--timeout-min 50]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "runpod-engine-smoke-test"))
from exec_pod import DEFAULT_KEY, get_ssh_cmd  # noqa: E402

OUTPUT_DIR = "/workspace/output/assembly-association"
LOG_DIR = "/workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-assembly-association/logs"


def ssh(host, port, cmd, timeout=40) -> tuple[int, str]:
    try:
        p = subprocess.run(get_ssh_cmd(host, port, DEFAULT_KEY, cmd), stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--poll", type=float, default=20.0)
    ap.add_argument("--timeout-min", type=float, default=50.0)
    a = ap.parse_args()
    stem = Path(a.params).stem
    marker = f"{OUTPUT_DIR}/{stem}.finished"
    log = f"{LOG_DIR}/session_{stem}.log"
    t_end = time.time() + 60 * a.timeout_min
    last = ""
    while time.time() < t_end:
        rc, out = ssh(a.host, a.port,
                      f"cat {marker} 2>/dev/null || echo RUNNING; "
                      f"grep -aE '^(PASS|FAIL|SKIP|STOP) ' {log} 2>/dev/null | tail -1")
        lines = out.splitlines()
        if rc == 0 and lines:
            status = lines[0].strip()
            progress = lines[1] if len(lines) > 1 else ""
            if progress and progress != last:
                print(f"[{time.strftime('%H:%M:%S')}] {progress}", flush=True)
                last = progress
            if status != "RUNNING":
                print(f"SESSION FINISHED exit={status}", flush=True)
                sys.exit(int(status) if status.lstrip('-').isdigit() else 1)
        time.sleep(a.poll)
    print("WAIT TIMEOUT", flush=True)
    sys.exit(124)


if __name__ == "__main__":
    main()
