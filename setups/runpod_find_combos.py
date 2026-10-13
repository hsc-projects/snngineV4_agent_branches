#!/usr/bin/env python3
"""
RunPod GPU/CPU Combo Finder & Stock Checker
===========================================
Queries RunPod's GraphQL API to find optimal, in-stock GPU/CPU pod combinations
matching budget, VRAM, and persistent network volume region constraints.

Uses only Python standard library (no pip dependencies required).
Reads credentials securely from setups/.secrets/.env.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_api_key(env_path: Path) -> str:
    """Reads RUNPOD_API_KEY from .env without echoing to logs."""
    if not env_path.exists():
        raise FileNotFoundError(f"Secrets file not found at {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("RUNPOD_API_KEY="):
                val = line.split("=", 1)[1].strip().strip("\"'")
                if val:
                    return val
    raise ValueError(f"RUNPOD_API_KEY not found in {env_path}")


def query_runpod_graphql(api_key: str, query: str) -> dict:
    """Executes a GraphQL query against RunPod API."""
    url = f"https://api.runpod.io/graphql?api_key={api_key}"
    payload = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if "errors" in res:
            raise RuntimeError(f"GraphQL query error: {res['errors']}")
        return res.get("data", {})


def fetch_account_and_volumes(api_key: str) -> tuple[dict, list, list]:
    query = """
    query Myself {
      myself {
        id
        networkVolumes {
          id
          name
          dataCenterId
          size
        }
        pods {
          id
          name
          desiredStatus
          imageName
          gpuCount
          machine {
            gpuDisplayName
          }
        }
      }
    }
    """
    data = query_runpod_graphql(api_key, query)
    user = data.get("myself", {})
    return user, user.get("networkVolumes", []), user.get("pods", [])


def fetch_gpu_stock(api_key: str) -> list[dict]:
    query = """
    query GpuTypes {
      gpuTypes {
        id
        displayName
        memoryInGb
        secureCloud
        communityCloud
        communityPrice
        lowestPrice(input: {gpuCount: 1}) {
          minimumBidPrice
          uninterruptablePrice
          stockStatus
        }
      }
    }
    """
    data = query_runpod_graphql(api_key, query)
    return data.get("gpuTypes", [])


def main():
    parser = argparse.ArgumentParser(description="Find optimal in-stock RunPod GPU combinations.")
    parser.add_argument("--min-vram", type=int, default=16, help="Minimum VRAM in GB (default: 16)")
    parser.add_argument("--max-price", type=float, default=1.00, help="Maximum price in $/hr (default: 1.00)")
    parser.add_argument("--secure-only", action="store_true", default=True,
                        help="Only include Secure Cloud GPUs (required for network volumes; default: True)")
    parser.add_argument("--allow-community", action="store_true", help="Include Community Cloud options")
    parser.add_argument("--all-stock", action="store_true", help="Show all GPUs regardless of stock status")
    args = parser.parse_args()

    # Locate secrets .env
    script_dir = Path(__file__).resolve().parent
    secrets_env = script_dir / ".secrets" / ".env"
    if not secrets_env.exists():
        secrets_env = script_dir.parent / "setups" / ".secrets" / ".env"

    try:
        api_key = load_api_key(secrets_env)
    except Exception as e:
        print(f"Error loading RunPod API key: {e}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("RunPod Live Stock & Optimization Inspector")
    print("=" * 80)

    if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # 1. Inspect account, volumes, pods
    try:
        user, volumes, pods = fetch_account_and_volumes(api_key)
        user_id = user.get("id", "Unknown")
        print(f"Authenticated User: {user_id}")
        
        print("\nPersistent Network Volumes:")
        if volumes:
            for v in volumes:
                print(f"  - ID: {v['id']} | Name: '{v['name']}' | Region: {v['dataCenterId']} | Size: {v['size']} GB")
        else:
            print("  (None found)")

        print(f"\nActive Pods: {len(pods)}")
        for p in pods:
            m = p.get("machine") or {}
            gpu_name = m.get("gpuDisplayName", "CPU")
            print(f"  - {p['id']}: '{p['name']}' | Status: {p.get('desiredStatus')} | GPU: {gpu_name}")
    except Exception as e:
        print(f"Warning: Could not fetch user/volume details ({e})", file=sys.stderr)

    # 2. Inspect live GPU stock
    try:
        gpus = fetch_gpu_stock(api_key)
    except Exception as e:
        print(f"Error fetching GPU types: {e}", file=sys.stderr)
        sys.exit(1)

    secure_filter = not args.allow_community

    matches = []
    for g in gpus:
        vram = g.get("memoryInGb") or 0
        lp = g.get("lowestPrice") or {}
        price = lp.get("uninterruptablePrice")
        stock = lp.get("stockStatus")
        is_secure = g.get("secureCloud", False)

        if vram < args.min_vram:
            continue
        if price is None or price > args.max_price:
            continue
        if secure_filter and not is_secure:
            continue
        if not args.all_stock and (stock is None or stock.lower() not in ["high", "medium", "low"]):
            continue

        matches.append({
            "id": g["id"],
            "name": g["displayName"],
            "vram": vram,
            "price": price,
            "stock": stock or "None",
            "secure": is_secure,
        })

    matches.sort(key=lambda x: (x["price"], -x["vram"]))

    print(f"\nOptimal Available GPU Options (Min {args.min_vram}GB VRAM, Max ${args.max_price:.2f}/hr):")
    print("-" * 80)
    print(f"{'GPU Model':<22} | {'VRAM':>5} | {'Price/hr':>10} | {'Stock':<8} | {'SecureCloud (Volume Ready)':<26}")
    print("-" * 80)

    if not matches:
        print("  No matching GPUs found with current filters. Try relaxing --max-price or --min-vram.")
    else:
        for idx, m in enumerate(matches):
            star = "* [Top Pick]" if idx == 0 else " "
            sec_str = "Yes (Volume compatible)" if m["secure"] else "No (Community only)"
            print(f"{m['name']:<22} | {m['vram']:>3}GB | ${m['price']:>7.2f}/hr | {m['stock']:<8} | {sec_str:<26} {star}")

    print("-" * 80)
    if matches and volumes:
        top = matches[0]
        vol = volumes[0]
        print("\nRecommended Next Step:")
        print(f"  Spin up 1x {top['name']} ({top['vram']}GB VRAM @ ${top['price']:.2f}/hr) in data center '{vol['dataCenterId']}'")
        print(f"  attaching network volume '{vol['id']}' mounted to '/workspace'.")
    print("=" * 80)


if __name__ == "__main__":
    main()
