#!/usr/bin/env python3
"""
RESTCONF API Root Discovery
===========================
Topology : ceos-fabric (Containerlab)
Target   : any Arista cEOS node (default: leaf3)
Port     : 6020 (HTTPS, management api restconf)
Auth     : admin / admin

Steps
-----
1. RFC 8040 well-known host-meta  →  find the RESTCONF root path
2. GET /restconf                  →  entry-point hrefs (data, operations)
3. YANG library version           →  RFC 7895 or 8525
4. Module list                    →  all supported YANG modules
"""

import json
import sys
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Topology
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

PORT     = 6020
USERNAME = "admin"
PASSWORD = "admin"

RC_HEADERS = {"Accept": "application/yang-data+json"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def session(host: str) -> requests.Session:
    s = requests.Session()
    s.auth    = (USERNAME, PASSWORD)
    s.verify  = False
    s.headers.update(RC_HEADERS)
    s.base    = f"https://{host}:{PORT}"
    return s


def get(s: requests.Session, path: str, **kwargs) -> requests.Response:
    url = s.base + path
    r = s.get(url, **kwargs)
    print(f"  GET {path:<55} {r.status_code}")
    return r


# ---------------------------------------------------------------------------
# Discovery steps
# ---------------------------------------------------------------------------
def discover(host: str, name: str = "") -> None:
    label = name or host
    print(f"\n{'='*65}")
    print(f"  Node : {label}   ({host}:{PORT})")
    print(f"{'='*65}")

    s = session(host)

    # ── 1. host-meta ─────────────────────────────────────────────────────────
    print("\n── 1. RFC 8040 well-known host-meta ─────────────────────────────")
    r = get(s, "/.well-known/host-meta",
            headers={"Accept": "application/xrd+xml"})
    rc_root = "/restconf"          # default if discovery fails
    if r.ok:
        print(f"  {r.text.strip()[:300]}")
        if 'rel="restconf"' in r.text:
            import re
            m = re.search(r'href="([^"]+)"', r.text)
            if m:
                rc_root = m.group(1)
    print(f"  → RESTCONF root: {rc_root}")

    # ── 2. RESTCONF entry point ───────────────────────────────────────────────
    print("\n── 2. RESTCONF entry point ──────────────────────────────────────")
    r = get(s, rc_root)
    if r.ok:
        print(json.dumps(r.json(), indent=4))
    else:
        print(f"  ERROR: {r.text[:200]}")
        return

    # ── 3. YANG library version ───────────────────────────────────────────────
    print("\n── 3. YANG library version ──────────────────────────────────────")
    r = get(s, f"{rc_root}/yang-library-version")
    if r.ok:
        print(f"  {r.json()}")

    # ── 4. Module list ────────────────────────────────────────────────────────
    print("\n── 4. Supported YANG modules ────────────────────────────────────")

    # Try RFC 7895 first, then RFC 8525
    r = get(s, f"{rc_root}/data/ietf-yang-library:modules-state")
    if r.ok:
        mods = (r.json()
                .get("ietf-yang-library:modules-state", {})
                .get("module", []))
        _print_modules(mods)
    else:
        r = get(s, f"{rc_root}/data/ietf-yang-library:yang-library")
        if r.ok:
            sets = (r.json()
                    .get("ietf-yang-library:yang-library", {})
                    .get("module-set", []))
            mods = sets[0].get("module", []) if sets else []
            _print_modules(mods)
        else:
            print("  Could not retrieve module list")


def _print_modules(mods: list) -> None:
    if not mods:
        print("  (empty)")
        return
    print(f"  {len(mods)} modules advertised\n")
    col = 52
    print(f"  {'name':<{col}} {'revision':<12} conformance")
    print(f"  {'-'*col} {'-'*12} -----------")
    for m in sorted(mods, key=lambda x: x.get("name", "")):
        print(f"  {m.get('name','?'):<{col}} "
              f"{m.get('revision','-'):<12} "
              f"{m.get('conformance-type', m.get('conformance','?'))}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Filter out Jupyter kernel args (--f=<kernel.json>, -f ..., etc.)
    real_args = [a for a in sys.argv[1:] if not a.startswith("-")]
    host = real_args[0] if real_args else NODES["leaf3"]
    name = next((n for n, ip in NODES.items() if ip == host), host)
    discover(host, name)
