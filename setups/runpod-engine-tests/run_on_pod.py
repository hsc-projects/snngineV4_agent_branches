"""
Run the engine tests on a Runpod pod (setups/runpod-engine-tests/README.md): upload a pack (pack_tree.sh) and the
pod script, start the run detached, wait for its marker, download the results to results/<run>/ and print the
summary. Standard library only; it runs nothing but ssh and scp locally.

  python run_on_pod.py --host HOST --port PORT --tree PACK.tgz --run NAME [--level quick|full]
                       [--configs small,odd] [--no-wait]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
KEY = os.path.join(REPO, "setups", ".secrets", "id_ed25519")
NULL = "NUL" if os.name == "nt" else "/dev/null"
OPTS = ["-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", f"UserKnownHostsFile={NULL}", "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=20"]


def ssh(host, port, cmd, timeout=120):
    p = subprocess.run(["ssh", *OPTS, "-p", str(port), f"root@{host}", cmd], capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def scp(host, port, src, dst, timeout=600):
    p = subprocess.run(["scp", "-O", *OPTS, "-P", str(port), src, dst], capture_output=True, text=True,
                       timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"scp {src} -> {dst} failed: {p.stderr.strip()}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--tree", required=True, help="pack from pack_tree.sh")
    ap.add_argument("--run", required=True, help="run name (results go to results/<run>/)")
    ap.add_argument("--level", choices=("quick", "full"), default="quick",
                    help="quick: the small configurations; full: all, including 7^3, 9^3 and D 16")
    ap.add_argument("--configs", default="", help="configurations to test instead of the level's, e.g. small,odd")
    ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--poll", type=float, default=30.0)
    ap.add_argument("--timeout-min", type=float, default=90.0)
    a = ap.parse_args(argv)
    h, p = a.host, a.port

    remote_tgz = f"/root/engine-tests-{a.run}.tgz"
    scp(h, p, a.tree, f"root@{h}:{remote_tgz}")
    scp(h, p, os.path.join(HERE, "pod_run_tests.sh"), f"root@{h}:/root/pod_run_tests.sh")
    rc, out = ssh(h, p, f"sed -i 's/\\r$//' /root/pod_run_tests.sh && md5sum {remote_tgz}")
    print(out.strip())
    start = (f"nohup bash /root/pod_run_tests.sh {remote_tgz} {a.run} {a.level} '{a.configs}' "
             f"> /root/engine-tests-{a.run}.log 2>&1 < /dev/null & disown; echo started")
    rc, out = ssh(h, p, start)
    print(out.strip())
    if rc != 0:
        sys.exit(f"start failed: {out}")
    if a.no_wait:
        return
    marker = f"/workspace/output/engine-tests/{a.run}/finished"
    t_end = time.time() + 60 * a.timeout_min
    while True:
        try:
            rc, out = ssh(h, p, f"cat {marker} 2>/dev/null || echo RUNNING")
        except subprocess.TimeoutExpired:
            rc, out = 1, ""
        state = out.strip().splitlines()[-1].strip() if out.strip() else ""
        if rc == 0 and state.lstrip("-").isdigit():     # the marker holds the run's exit code
            break
        if time.time() > t_end:
            sys.exit(f"timeout after {a.timeout_min} min; the run continues on the pod ({marker})")
        time.sleep(a.poll)
    dest = os.path.join(HERE, "results", a.run)
    os.makedirs(dest, exist_ok=True)
    scp(h, p, f"root@{h}:/workspace/output/engine-tests/{a.run}/results.tgz", os.path.join(dest, "results.tgz"))
    subprocess.run(["tar", "-xzf", "results.tgz"], cwd=dest, check=False)
    summary = os.path.join(dest, "summary.txt")
    print(open(summary).read() if os.path.exists(summary) else f"no summary in {dest}")
    print(f"exit {state}; results in {dest}")


if __name__ == "__main__":
    main()
