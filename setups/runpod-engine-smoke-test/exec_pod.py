#!/usr/bin/env python3
"""
Host-side SSH/SCP automation client for Runpod Engine Smoke Test.
Handles Windows-specific OpenSSH ACL constraints, stdin detachment,
file transfer, and remote test runner execution.
"""

import argparse
import getpass
import os
import subprocess
import sys
import time
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_KEY = REPO_ROOT / "setups" / ".secrets" / "id_ed25519"
KNOWN_HOSTS = SCRIPT_DIR / ".pod_known_hosts"


def fix_key_permissions(key_path: Path):
    # Skip icacls to prevent interactive prompt hanging
    pass



def get_ssh_cmd(host: str, port: int, key_path: Path, remote_cmd: str) -> list[str]:
    return [
        "ssh",
        "-F", os.devnull,
        "-i", str(key_path),
        "-p", str(port),
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=15",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        f"root@{host}",
        remote_cmd,
    ]


def run_ssh(host: str, port: int, key_path: Path, remote_cmd: str, timeout: int = 180) -> int:
    cmd = get_ssh_cmd(host, port, key_path, remote_cmd)
    print(f"\n[*] Executing remote SSH on {host}:{port}...")
    print(f"[*] Command: {remote_cmd}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        for line in proc.stdout:
            try:
                sys.stdout.write(line)
                sys.stdout.flush()
            except UnicodeEncodeError:
                sys.stdout.write(line.encode("ascii", errors="replace").decode("ascii"))
                sys.stdout.flush()
        proc.wait(timeout=timeout)
        return proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"\n[-] Command timed out after {timeout}s", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[-] Execution failed: {e}", file=sys.stderr)
        return 1


def run_scp(host: str, port: int, key_path: Path, local_path: Path, remote_path: str, timeout: int = 60) -> int:
    cmd = [
        "scp",
        "-F", os.devnull,
        "-i", str(key_path),
        "-P", str(port),
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=15",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        "-r",
        str(local_path),
        f"root@{host}:{remote_path}",
    ]
    print(f"\n[*] Transferring {local_path} -> root@{host}:{remote_path} via SCP...")
    try:
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if res.returncode == 0:
            print("[+] SCP transfer successful.")
            return 0
        else:
            print(f"[-] SCP failed (exit {res.returncode}):\n{res.stderr}", file=sys.stderr)
            return res.returncode
    except Exception as e:
        print(f"[-] SCP exception: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
            sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Runpod Pod Remote Automation Client")
    parser.add_argument("--host", required=True, help="Pod IP or hostname")
    parser.add_argument("--port", type=int, default=22, help="Direct SSH port")
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY, help="Path to private SSH key")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Subcommand: cmd
    cmd_parser = subparsers.add_parser("cmd", help="Execute remote command over SSH")
    cmd_parser.add_argument("command", help="Command string to execute")
    cmd_parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")

    # Subcommand: sync
    sync_parser = subparsers.add_parser("sync", help="Sync local files to remote pod")
    sync_parser.add_argument("--src", type=Path, default=SCRIPT_DIR, help="Local source path")
    sync_parser.add_argument("--dest", default="/workspace/snngineV4_agent_branches/setups/", help="Remote destination path")

    args = parser.parse_args()

    fix_key_permissions(args.key)

    if args.action == "cmd":
        rc = run_ssh(args.host, args.port, args.key, args.command, timeout=args.timeout)
        sys.exit(rc)
    elif args.action == "sync":
        rc = run_scp(args.host, args.port, args.key, args.src, args.dest)
        sys.exit(rc)
