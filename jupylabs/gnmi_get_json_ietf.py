#!/usr/bin/env python3
"""
gnmi_get_json_ietf.py — Module 2 precursor
===========================================
Demonstrates json_ietf encoding via gNMI Get RPC against Arista cEOS.

Steps:
  1  Single interface state (Ethernet1)
  2  All interfaces — json vs json_ietf side-by-side comparison
  3  BGP neighbour state (raw json_ietf response)
  4  BGP neighbour state (parsed and tabulated)

Usage:
  python gnmi_get_json_ietf.py --step 1
  python gnmi_get_json_ietf.py --step 2
  python gnmi_get_json_ietf.py --step 3
  python gnmi_get_json_ietf.py --step 4
  python gnmi_get_json_ietf.py --all
"""

import argparse
import json
import sys
from pygnmi.client import gNMIclient

# ---------------------------------------------------------------------------
# Connection parameters — spine1
# ---------------------------------------------------------------------------
TARGET   = ("172.60.60.21", 6030)
USERNAME = "admin"
PASSWORD = "admin"


def open_client() -> gNMIclient:
    return gNMIclient(
        target=TARGET,
        username=USERNAME,
        password=PASSWORD,
        insecure=True,
    )


def pretty(data: dict) -> str:
    return json.dumps(data, indent=2)


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Step 1 — Single interface state in json_ietf
# ---------------------------------------------------------------------------
def step1() -> None:
    section("STEP 1 — Ethernet1 state (json_ietf)")

    path = "/interfaces/interface[name=Ethernet1]/state"

    with open_client() as gc:
        response = gc.get(
            path=[path],
            datatype="state",         # operational state only
            encoding="json_ietf",
        )

    print(f"\nPath queried : {path}")
    print(f"Encoding     : json_ietf\n")

    # The response is a dict: {"notification": [{"update": [{"path": ..., "val": ...}]}]}
    updates = response.get("notification", [{}])[0].get("update", [])

    for update in updates:
        returned_path = update.get("path", "")
        val           = update.get("val", {})
        print(f"Returned path : {returned_path}")
        print(f"\nPayload (json_ietf):\n{pretty(val)}")

    print("\n--- What to observe ---")
    print("  admin-status / oper-status  : enum strings (e.g. 'UP')")
    print("  type                        : 'iana-if-type:ethernetCsmacd' — note the module prefix")
    print("  counters                    : raw uint64 integers (no units suffix)")


# ---------------------------------------------------------------------------
# Step 2 — All interfaces: json vs json_ietf
# ---------------------------------------------------------------------------
def unwrap_interfaces(val: dict) -> list:
    """
    EOS may nest the interface list under several key variants.
    Try each in order and return the first non-empty list found.
    """
    candidates = [
        # json_ietf — double-wrapped: interfaces container then interface list
        val.get("openconfig-interfaces:interfaces", {})
           .get("openconfig-interfaces:interface"),
        val.get("openconfig-interfaces:interfaces", {})
           .get("interface"),
        # json — same structure, no module prefix
        val.get("interfaces", {}).get("interface"),
        # pygnmi sometimes strips the outer container
        val.get("openconfig-interfaces:interface"),
        val.get("interface"),
    ]
    for c in candidates:
        if c:
            return c
    return []


def get_field(d: dict, *keys: str, default="n/a"):
    """Try multiple key names and return the first match."""
    for k in keys:
        if k in d:
            return d[k]
    return default


def extract_name(intf: dict) -> str:
    """
    EOS returns the name as a prefixed key inside the list entry.
    The key is 'openconfig-interfaces:name' regardless of encoding.
    """
    for k in ("openconfig-interfaces:name", "name"):
        if k in intf:
            return intf[k]
    return "n/a"


def extract_type(intf: dict) -> str:
    """
    Pull the interface type from the state container.
    Both 'state' and 'openconfig-interfaces:state' are tried.
    Returns the raw value — caller decides how to display it.
    """
    state = intf.get("openconfig-interfaces:state") or intf.get("state") or {}
    for k in ("openconfig-interfaces:type", "type"):
        if k in state:
            return state[k]
    return "n/a"


def step2(debug: bool = False) -> None:
    section("STEP 2 — All interfaces: json vs json_ietf comparison")

    # Target a single interface to keep the payload small and readable
    # Use Ethernet1 — confirmed connected from 'show interfaces status'
    path_single = "/interfaces/interface[name=Ethernet1]/state"

    with open_client() as gc:
        resp_json = gc.get(path=[path_single], datatype="state", encoding="json")
        resp_ietf = gc.get(path=[path_single], datatype="state", encoding="json_ietf")

    def extract_val(resp: dict) -> dict:
        return (
            resp.get("notification", [{}])[0]
                .get("update", [{}])[0]
                .get("val", {})
        )

    val_json = extract_val(resp_json)
    val_ietf = extract_val(resp_ietf)

    if debug:
        print("\n[DEBUG] json response keys:")
        print("  ", list(val_json.keys()))
        print("\n[DEBUG] json_ietf response keys:")
        print("  ", list(val_ietf.keys()))
        print("\n[DEBUG] json full value:")
        print(pretty(val_json))
        print("\n[DEBUG] json_ietf full value:")
        print(pretty(val_ietf))
        return

    # -----------------------------------------------------------------------
    # The identityref difference lives in the 'type' leaf.
    # EOS encodes it differently per encoding:
    #   json      -> bare short-form:   "ethernetCsmacd"
    #   json_ietf -> module-prefixed:   "iana-if-type:ethernetCsmacd"
    # We pull every leaf that exists in both and show them side by side.
    # -----------------------------------------------------------------------

    # Collect all leaf keys present in either response (skip nested dicts/lists)
    all_keys = sorted(
        set(
            k.replace("openconfig-interfaces:", "") for k in list(val_json.keys()) + list(val_ietf.keys())
            if not isinstance(val_json.get(k) or val_ietf.get(k), (dict, list))
        )
    )

    def lookup(val: dict, bare_key: str) -> str:
        """Try prefixed then bare key, return string representation."""
        for k in (f"openconfig-interfaces:{bare_key}", bare_key):
            if k in val:
                return str(val[k])
        return "—"

    print(f"\n  {'Leaf':<30} {'json':<40} {'json_ietf'}")
    print(f"  {'-'*30} {'-'*40} {'-'*35}")

    for key in all_keys:
        v_json = lookup(val_json, key)
        v_ietf = lookup(val_ietf, key)
        # Highlight rows where the two encodings differ
        marker = " ◀" if v_json != v_ietf else ""
        print(f"  {key:<30} {v_json:<40} {v_ietf}{marker}")

    print("\n--- What to observe ---")
    print("  Rows marked ◀ are where json and json_ietf differ.")
    print("  'type' leaf  : json='ethernetCsmacd'  vs  json_ietf='iana-if-type:ethernetCsmacd'")
    print("  admin-status : json='UP'               vs  json_ietf='UP'  (enum, same here)")
    print("  Counters and integers are identical in both encodings.")
    print("  The module prefix on identityref leaves is what makes json_ietf portable.")


# ---------------------------------------------------------------------------
# Step 3 — BGP neighbour state (raw json_ietf)
# ---------------------------------------------------------------------------
def step3() -> None:
    section("STEP 3 — BGP neighbours (raw json_ietf)")

    path = (
        "/network-instances/network-instance[name=default]"
        "/protocols/protocol[identifier=BGP][name=BGP]"
        "/bgp/neighbors"
    )

    with open_client() as gc:
        response = gc.get(
            path=[path],
            datatype="state",
            encoding="json_ietf",
        )

    updates = response.get("notification", [{}])[0].get("update", [])

    for update in updates:
        val = update.get("val", {})
        print(f"\nPayload (json_ietf):\n{pretty(val)}")

    print("\n--- What to observe ---")
    print("  session-state : 'ESTABLISHED' for 10.0.0.11, 10.0.0.12, 10.0.0.22")
    print("  session-state : 'ACTIVE' for 10.0.0.13, 10.0.0.14, 10.0.0.15 (leaves not up)")
    print("  Values are plain enum strings — no module prefix on session-state in OC BGP model")
    print("  prefixes-received : 0 for all (no host routes being advertised yet)")


# ---------------------------------------------------------------------------
# Step 4 — BGP neighbour state (parsed and tabulated)
# ---------------------------------------------------------------------------
def step4() -> None:
    section("STEP 4 — BGP neighbours (parsed)")

    path = (
        "/network-instances/network-instance[name=default]"
        "/protocols/protocol[identifier=BGP][name=BGP]"
        "/bgp/neighbors"
    )

    with open_client() as gc:
        response = gc.get(
            path=[path],
            datatype="state",
            encoding="json_ietf",
        )

    val = (
        response
        .get("notification", [{}])[0]
        .get("update", [{}])[0]
        .get("val", {})
    )

    # Navigate to neighbor list — key may be prefixed or bare depending on EOS version
    neighbor_list = (
        val.get("openconfig-network-instance:neighbor")
        or val.get("neighbor")
        or []
    )

    print(f"\n  {'Neighbour':<16} {'AS':<8} {'Session State':<16} {'Uptime (s)':<12} {'Pfx Rcvd'}")
    print(f"  {'-'*16} {'-'*8} {'-'*16} {'-'*12} {'-'*9}")

    for nbr in neighbor_list:
        # peer-address is a key leaf — may sit at top level or under state
        peer_addr  = nbr.get("neighbor-address") or nbr.get("peer-address", "n/a")
        state_data = nbr.get("state", nbr)          # fall back to top-level if no state container

        peer_as    = state_data.get("peer-as", "n/a")
        sess_state = state_data.get("session-state", "n/a")
        uptime_ns  = state_data.get("established-transitions", 0)   # fallback counter

        # Uptime in seconds — OC path is timers/state/uptime
        timers     = nbr.get("timers", {})
        timer_state = timers.get("state", {})
        uptime_s   = timer_state.get("uptime", 0)

        # Prefix counts
        afi_safis  = nbr.get("afi-safis", {}).get("afi-safi", [])
        pfx_rcvd   = 0
        for afi in afi_safis:
            pfx_rcvd += (
                afi.get("state", {})
                .get("prefixes", {})
                .get("received", 0)
            )

        print(f"  {peer_addr:<16} {str(peer_as):<8} {sess_state:<16} {str(uptime_s):<12} {pfx_rcvd}")

    print("\n--- What to observe ---")
    print("  ESTABLISHED peers : 10.0.0.11, 10.0.0.12, 10.0.0.22 — uptime > 0")
    print("  ACTIVE peers      : 10.0.0.13, 10.0.0.14, 10.0.0.15 — uptime = 0")
    print("  prefixes-received : 0 across all — no host prefixes in fabric yet")
    print("  This parsed dict is what you would push to Prometheus as gauge metrics in Module 3.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
STEPS = {
    "1": step1,
    "2": step2,
    "3": step3,
    "4": step4,
}

def main() -> None:
    parser = argparse.ArgumentParser(
        description="gNMI json_ietf encoding demo — Arista cEOS fabric"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--step",
        choices=STEPS.keys(),
        help="Run a single step (1-4)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Run all four steps in sequence",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Step 2 only: print raw top-level response keys instead of the table",
    )
    args = parser.parse_args()

    if args.all:
        for fn in STEPS.values():
            fn()
    elif args.step == "2":
        step2(debug=args.debug)
    else:
        STEPS[args.step]()


if __name__ == "__main__":
    main()
