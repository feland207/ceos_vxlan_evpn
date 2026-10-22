---

VRF assignment (authoritative — readme wins)

┌──────────────┬──────────┬──────┬─────────────────┬───────┬───────┬─────────┐
│     Node     │   VRF    │ VLAN │     Subnet      │ L2VNI │ L3VNI │   RT    │
├──────────────┼──────────┼──────┼─────────────────┼───────┼───────┼─────────┤
│ leaf1, leaf2 │ TENANT_A │ 10   │ 192.168.10.0/24 │ 10010 │ 50010 │ 100:100 │
├──────────────┼──────────┼──────┼─────────────────┼───────┼───────┼─────────┤
│ leaf3, leaf4 │ TENANT_A │ 10   │ 192.168.10.0/24 │ 10010 │ 50010 │ 100:100 │
├──────────────┼──────────┼──────┼─────────────────┼───────┼───────┼─────────┤
│ leaf5        │ TENANT_B │ 20   │ 192.168.20.0/24 │ 10020 │ 50020 │ 200:200 │
└──────────────┴──────────┴──────┴─────────────────┴───────┴───────┴─────────┘

▎ leaf3/4 currently have TENANT_B in their startup-configs — the scenario 2 playbook will clean this up and apply TENANT_A.

---

Role inventory

roles/
  validate_underlay/          ← done ✓

  # ── EOS configuration roles ──────────────────────────
  eos_vxlan_flood/            # Scenario 1 — VLAN10 + Vxlan1 + static HER on leaf3/4/5
  eos_vxlan_evpn/             # Scenario 2 — BGP EVPN AF, L2/L3VNI, TENANT_A(3/4) + TENANT_B(5)
  eos_esi_lag/                # Scenario 3 — Port-Channel10 + ESI on leaf1/2 + TENANT_A

  # ── Linux configuration roles ─────────────────────────
  linux_eth_simple/           # Flat IP on eth1 — host2/3/4 (IP varies per scenario via host_vars)
  linux_bond_lacp/            # LACP bond0 over eth1+eth2 — host1 scenario 3

  # ── Validation roles ──────────────────────────────────
  validate_scenario1/         # VXLAN flood state: VNI map, flood lists, MAC learning
  validate_scenario2/         # EVPN overlay: BGP EVPN all-leaves Established, Type-2/3/5 routes
  validate_scenario3/         # ESI: Port-Channel up, Type-1/4 routes, DF election
  validate_linux_connectivity/ # Ping tests from hosts (gateway + fabric peers)

---

The 6 playbooks

┌─────┬───────────────────────────────┬──────────────────────────────────────────────────────────────────────┬───────────────┐
│  #  │             File              │                             Plays inside                             │     Tags      │
├─────┼───────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────────┤
│ 1   │ scenario1_flood_and_learn.yml │ leaf3/4/5 → eos_vxlan_flood; host2/3/4 → linux_eth_simple            │ deploy,       │
│     │                               │                                                                      │ cleanup       │
├─────┼───────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────────┤
│ 2   │ validate_scenario1.yml        │ leaf3/4/5 → validate_scenario1; host2/3/4 →                          │ —             │
│     │                               │ validate_linux_connectivity                                          │               │
├─────┼───────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────────┤
│ 3   │ scenario2_evpn_overlay.yml    │ leaf3/4/5 → eos_vxlan_evpn; host2/3 → linux_eth_simple; host4 →      │ deploy,       │
│     │                               │ linux_eth_simple                                                     │ cleanup       │
├─────┼───────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────────┤
│ 4   │ validate_scenario2.yml        │ leaf3/4/5 → validate_scenario2; host2/3/4 →                          │ —             │
│     │                               │ validate_linux_connectivity                                          │               │
├─────┼───────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────────┤
│ 5   │ scenario3_esi_multihoming.yml │ leaf1/2 → eos_esi_lag; host1 → linux_bond_lacp; host2 →              │ deploy,       │
│     │                               │ linux_eth_simple                                                     │ cleanup       │
├─────┼───────────────────────────────┼──────────────────────────────────────────────────────────────────────┼───────────────┤
│ 6   │ validate_scenario3.yml        │ leaf1/2 → validate_scenario3; host1/2 → validate_linux_connectivity  │ —             │
└─────┴───────────────────────────────┴──────────────────────────────────────────────────────────────────────┴───────────────┘

---

Workflow

# Run underlay health check first (already works)
ansible-playbook playbooks/validate_underlay.yml

# ── Scenario 1 ─────────────────────────────────────────
ansible-playbook playbooks/scenario1_flood_and_learn.yml          # deploy
ansible-playbook playbooks/validate_scenario1.yml                 # validate
ansible-playbook playbooks/scenario1_flood_and_learn.yml --tags cleanup

# ── Scenario 2 ─────────────────────────────────────────
ansible-playbook playbooks/scenario2_evpn_overlay.yml
ansible-playbook playbooks/validate_scenario2.yml
ansible-playbook playbooks/scenario2_evpn_overlay.yml --tags cleanup

# ── Scenario 3 ─────────────────────────────────────────
ansible-playbook playbooks/scenario3_esi_multihoming.yml
ansible-playbook playbooks/validate_scenario3.yml
ansible-playbook playbooks/scenario3_esi_multihoming.yml --tags cleanup

---
Full plan is locked:

┌──────────────────────┬──────────────┬────────────────────────────────────────────────────┐
│       Scenario       │ EOS targets  │                   Linux targets                    │
├──────────────────────┼──────────────┼────────────────────────────────────────────────────┤
│ 1 — Flood & Learn    │ leaf3/4/5    │ host2/3/4 (all VLAN10)                             │
├──────────────────────┼──────────────┼────────────────────────────────────────────────────┤
│ 2 — BGP EVPN         │ leaf3/4/5    │ host2/3 (VLAN10/TENANT_A), host4 (VLAN20/TENANT_B) │
├──────────────────────┼──────────────┼────────────────────────────────────────────────────┤
│ 3 — ESI Multi-Homing │ leaf1/2 only │ host1 only (bond0 LACP)                            │
└──────────────────────┴──────────────┴────────────────────────────────────────────────────┘
