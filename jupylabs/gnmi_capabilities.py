#!/usr/bin/env python3
"""
Module 1 — gNMI Connectivity & Capabilities
============================================
Topology : ceos-fabric (Containerlab)
Target   : any Arista cEOS node (default: spine1)
Port     : 6030 (Arista gNMI, no TLS)
Auth     : admin / admin

Usage:
    python gnmi_capabilities.py                        # spine1 (default)
    python gnmi_capabilities.py --host 172.60.60.11    # leaf1
    python gnmi_capabilities.py --all                  # all nodes in topology
"""

import argparse
import json
from pygnmi.client import gNMIclient

# ---------------------------------------------------------------------------
# Topology node map — matches ceos_clos.yml mgmt IPs
# ---------------------------------------------------------------------------
NODES = {
    "spine1": "172.60.60.21",
    "spine2": "172.60.60.22",
    "leaf1":  "172.60.60.11",
    "leaf2":  "172.60.60.12",
    "leaf3":  "172.60.60.13",
    "leaf4":  "172.60.60.14",
    "leaf5":  "172.60.60.15",
}

GNMI_PORT = 6030
USERNAME   = "admin"
PASSWORD   = "admin"


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------
def get_capabilities(host: str, name: str = "") -> dict | None:
    """
    Open a gNMI session to host:GNMI_PORT and issue a CapabilityRequest.
    Returns the parsed capability dict or None on failure.
    """
    label = name or host
    print(f"\n{'='*60}")
    print(f"  Node   : {label}")
    print(f"  Target : {host}:{GNMI_PORT}")
    print(f"{'='*60}")

    try:
        with gNMIclient(
            target=(host, GNMI_PORT),
            username=USERNAME,
            password=PASSWORD,
            insecure=True,          # No TLS on cEOS port 6030
        ) as gc:
            caps = gc.capabilities()

        # --- gNMI version ---
        gnmi_ver = caps.get("gnmi_version", "n/a")
        print(f"\n  gNMI version     : {gnmi_ver}")

        # --- Supported encodings ---
        encodings = caps.get("supported_encodings", [])
        print(f"  Encodings        : {', '.join(encodings) if encodings else 'n/a'}")

        # --- Supported models ---
        models = caps.get("supported_models", [])
        print(f"\n  Supported models : {len(models)} advertised")
        print(f"  {'-'*54}")

        # Group by organisation for readability
        by_org: dict[str, list] = {}
        for m in models:
            org = m.get("organization", "unknown")
            by_org.setdefault(org, []).append(m)

        for org, org_models in sorted(by_org.items()):
            print(f"\n  [{org}]")
            for m in sorted(org_models, key=lambda x: x.get("name", "")):
                name_str    = m.get("name", "n/a")
                version_str = m.get("version", "n/a")
                print(f"    {name_str:<55} ver: {version_str}")

        print(f"\n  ✓ Session closed cleanly\n")
        return caps

    except Exception as exc:
        print(f"\n  ✗ FAILED — {exc}\n")
        return None


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------
def print_summary(results: dict[str, dict | None]) -> None:
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    ok  = [n for n, r in results.items() if r is not None]
    err = [n for n, r in results.items() if r is None]
    for n in ok:
        ver = results[n].get("gNMI_version", "?")
        enc = ", ".join(results[n].get("supported_encodings", []))
        mdl = len(results[n].get("supported_models", []))
        print(f"  ✓ {n:<10}  gNMI {ver}  |  encodings: {enc}  |  models: {mdl}")
    for n in err:
        print(f"  ✗ {n:<10}  unreachable or auth failure")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="gNMI Capabilities probe for ceos-fabric lab"
    )
    parser.add_argument(
        "--host",
        help="Target mgmt IP (default: spine1 172.60.60.21)",
        default=None,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run against all nodes defined in NODES dict",
    )
    args = parser.parse_args()

    if args.all:
        results = {}
        for node_name, node_ip in NODES.items():
            results[node_name] = get_capabilities(node_ip, name=node_name)
        print_summary(results)
    else:
        host = args.host or NODES["spine1"]
        name = next((n for n, ip in NODES.items() if ip == host), host)
        get_capabilities(host, name=name)


if __name__ == "__main__":
    main()
