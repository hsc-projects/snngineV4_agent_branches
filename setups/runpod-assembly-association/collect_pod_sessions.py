#!/usr/bin/env python3
"""
Wait for detached sessions on several pods, then tar + download + extract each one's output.

  python collect_pod_sessions.py <pods.csv> <local output dir> <local params dir>

pods.csv columns: letter,id,host,port,params (params = parameter file name). Polls every 45 s,
gives up after 70 min; prints one DONE line per session and the letters still pending, and exits
with code 1 if any session is still pending.
"""
import csv, json, subprocess, sys, tarfile, time
from pathlib import Path

rows = list(csv.DictReader(open(sys.argv[1])))
dest = Path(sys.argv[2])
key = str(Path(__file__).resolve().parents[1] / ".secrets" / "id_ed25519")
OUT = "/workspace/output/assembly-association"
opts = ["-F", "NUL", "-i", key, "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
        "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=NUL"]

def ssh(r, cmd, t=120):
    return subprocess.run(["ssh", *opts, "-p", r["port"], f"root@{r['host']}", cmd], capture_output=True,
                          text=True, timeout=t).stdout.strip()

pending = {r["letter"]: r for r in rows}
deadline = time.time() + 70 * 60
while pending and time.time() < deadline:
    for L, r in list(pending.items()):
        stem = r["params"][:-5]
        try:
            st = ssh(r, f"cat {OUT}/{stem}.finished 2>/dev/null || echo RUNNING")
        except Exception as e:
            print(L, "ssh error", e, flush=True)
            continue
        if st == "RUNNING":
            continue
        sess = json.load(open(Path(sys.argv[3]) / r["params"]))["session"]
        ssh(r, f"cd {OUT} && tar czf {OUT}/{sess}.tgz {sess}", 300)
        subprocess.run(["scp", "-O", *opts, "-P", r["port"], f"root@{r['host']}:{OUT}/{sess}.tgz", str(dest)],
                       capture_output=True, timeout=600)
        tgz = dest / f"{sess}.tgz"
        if tgz.exists():
            with tarfile.open(tgz) as tf:
                tf.extractall(dest)
            print(f"{L} DONE exit={st} {sess} {time.strftime('%H:%M:%S')}", flush=True)
            del pending[L]
        else:
            print(L, "download failed", flush=True)
    if pending:
        time.sleep(45)
print("PENDING", sorted(pending) if pending else "none")
sys.exit(1 if pending else 0)   # non-zero while a session is still on the pod: do not terminate it yet
