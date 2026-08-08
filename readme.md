# EVPN-VXLAN Lab — IP Plan & Configuration Reference

Topology: `ceos_clos.yml` (2 spines, 5 leaves, 4 hosts) — mgmt network `172.60.60.0/24`

Design: ISIS underlay (single area), single-AS iBGP overlay, spine1/spine2 as
Route-Reflectors, VLAN-based EVPN service model, symmetric IRB with two VRFs.

---

## 1. IP Plan

### 1.1 Management (already defined in the YAML)

| Node   | Mgmt IP        |
|--------|-----------------|
| spine1 | 172.60.60.21    |
| spine2 | 172.60.60.22    |
| leaf1  | 172.60.60.11    |
| leaf2  | 172.60.60.12    |
| leaf3  | 172.60.60.13    |
| leaf4  | 172.60.60.14    |
| leaf5  | 172.60.60.15    |
| host1  | 172.60.60.31    |
| host2  | 172.60.60.32    |
| host3  | 172.60.60.33    |
| host4  | 172.60.60.34    |

### 1.2 Loopback0 — ISIS router-id / BGP router-id / VTEP source

| Node   | Loopback0    |
|--------|--------------|
| spine1 | 10.0.0.21/32  |
| spine2 | 10.0.0.22/32  |
| leaf1  | 10.0.0.11/32 |
| leaf2  | 10.0.0.12/32 |
| leaf3  | 10.0.0.13/32 |
| leaf4  | 10.0.0.14/32 |
| leaf5  | 10.0.0.15/32 |

### 1.3 P2P underlay links (/30) — scheme `10.<spine#>.<leaf#>.0/30`

| Link             | Subnet        | Spine side           | Leaf side            |
|------------------|---------------|-----------------------|------------------------|
| spine1–leaf1     | 10.1.1.0/30   | spine1 Et1 = .1        | leaf1 Et1 = .2          |
| spine1–leaf2     | 10.1.2.0/30   | spine1 Et2 = .1        | leaf2 Et1 = .2          |
| spine1–leaf3     | 10.1.3.0/30   | spine1 Et3 = .1        | leaf3 Et1 = .2          |
| spine1–leaf4     | 10.1.4.0/30   | spine1 Et4 = .1        | leaf4 Et1 = .2          |
| spine1–leaf5     | 10.1.5.0/30   | spine1 Et5 = .1        | leaf5 Et1 = .2          |
| spine2–leaf1     | 10.2.1.0/30   | spine2 Et1 = .1        | leaf1 Et2 = .2          |
| spine2–leaf2     | 10.2.2.0/30   | spine2 Et2 = .1        | leaf2 Et2 = .2          |
| spine2–leaf3     | 10.2.3.0/30   | spine2 Et3 = .1        | leaf3 Et2 = .2          |
| spine2–leaf4     | 10.2.4.0/30   | spine2 Et4 = .1        | leaf4 Et2 = .2          |
| spine2–leaf5     | 10.2.5.0/30   | spine2 Et5 = .1        | leaf5 Et2 = .2          |

### 1.4 Overlay (host-facing) subnets

| VLAN/VNI              | Subnet             | Anycast GW    | VRF        | Leaves     | L3VNI  |
|------------------------|---------------------|----------------|------------|------------|--------|
| VLAN10 / L2VNI 10010    | 192.168.10.0/24     | 192.168.10.1   | TENANT_A   | leaf1-4    | 50010  |
| VLAN20 / L2VNI 10020    | 192.168.20.0/24     | 192.168.20.1   | TENANT_B   | leaf5      | 50020  |

| Host  | Attached leaf(s)  | Data IP            |
|-------|--------------------|----------------------|
| host1 | leaf1 + leaf2 (ESI-LAG bond0) | 192.168.10.31/24 |
| host2 | leaf3              | 192.168.10.32/24    |
| host3 | leaf4              | 192.168.10.33/24    |
| host4 | leaf5              | 192.168.20.34/24    |

### 1.5 RD / RT scheme

| Scope             | RD pattern            | RT (common, must match to import) |
|--------------------|-------------------------|--------------------------------------|
| VLAN10 (per leaf)  | `<leaf-loopback>:10`     | `10:10`                              |
| VLAN20 (leaf5)     | `<leaf-loopback>:20`     | `20:20`                              |
| VRF TENANT_A       | `<leaf-loopback>:100`    | `100:100`                            |
| VRF TENANT_B       | `<leaf-loopback>:200`    | `200:200`                            |

Note: TENANT_A and TENANT_B use **different RTs on purpose** — no route
leaking, so host4 will not reach host1/2/3. That's intended VRF isolation,
not a bug — good talking point for the interview.

### 1.6 ESI (ethernet-segment) for host1's dual-homed link

| Leaf  | Port          | ESI                          |
|-------|----------------|-------------------------------|
| leaf1 | Port-Channel1  | `0000:0000:0000:1001:0001`    |
| leaf2 | Port-Channel1  | `0000:0000:0000:1001:0001`  (same ESI = same Ethernet Segment) |

---

## 2. cEOS configs

### spine1 (10.0.0.21)

```
hostname spine1
!
interface Loopback0
   ip address 10.0.0.21/32
   isis enable UNDERLAY
   isis passive
   exit
!
interface Ethernet1
   description "link-to-leaf1"
   no switchport
   ip address 10.1.1.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet2
   description "link-to-leaf2"
   no switchport
   ip address 10.1.2.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet3
   description "link-to-leaf3"
   no switchport
   ip address 10.1.3.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet4
   description "link-to-leaf4"
   no switchport
   ip address 10.1.4.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet5
   description "link-to-leaf5"
   no switchport
   ip address 10.1.5.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
router isis UNDERLAY
   net 49.0001.0000.0000.0021.00
   is-type level-2
   log-adjacency-changes
   address-family ipv4 unicast
      exit
   exit
!
router bgp 65000
   router-id 10.0.0.21
   no bgp default ipv4-unicast
   neighbor RR-PEER peer group
   neighbor RR-PEER remote-as 65000
   neighbor RR-PEER update-source Loopback0
   neighbor RR-PEER send-community extended
   neighbor 10.0.0.22 peer group RR-PEER
   !
   neighbor EVPN-CLIENT peer group
   neighbor EVPN-CLIENT remote-as 65000
   neighbor EVPN-CLIENT update-source Loopback0
   neighbor EVPN-CLIENT send-community extended
   neighbor EVPN-CLIENT route-reflector-client
   neighbor 10.0.0.11 peer group EVPN-CLIENT
   neighbor 10.0.0.12 peer group EVPN-CLIENT
   neighbor 10.0.0.13 peer group EVPN-CLIENT
   neighbor 10.0.0.14 peer group EVPN-CLIENT
   neighbor 10.0.0.15 peer group EVPN-CLIENT
   !
   address-family evpn
      neighbor RR-PEER activate
      neighbor EVPN-CLIENT activate
      exit
   exit
!
ip routing
!
end
```

### spine2 (10.0.0.22)

```
hostname spine2
!
interface Loopback0
   ip address 10.0.0.22/32
   isis enable UNDERLAY
   isis passive
   exit
!
interface Ethernet1
   description "link-to-leaf1"
   no switchport
   ip address 10.2.1.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet2
   description "link-to-leaf2"
   no switchport
   ip address 10.2.2.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet3
   description "link-to-leaf3"
   no switchport
   ip address 10.2.3.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet4
   description "link-to-leaf4"
   no switchport
   ip address 10.2.4.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet5
   description "link-to-leaf5"
   no switchport
   ip address 10.2.5.1/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
router isis UNDERLAY
   net 49.0001.0000.0000.0022.00
   is-type level-2
   log-adjacency-changes
   address-family ipv4 unicast
      exit
   exit
!
router bgp 65000
   router-id 10.0.0.22
   no bgp default ipv4-unicast
   neighbor RR-PEER peer group
   neighbor RR-PEER remote-as 65000
   neighbor RR-PEER update-source Loopback0
   neighbor RR-PEER send-community extended
   neighbor 10.0.0.21 peer group RR-PEER
   !
   neighbor EVPN-CLIENT peer group
   neighbor EVPN-CLIENT remote-as 65000
   neighbor EVPN-CLIENT update-source Loopback0
   neighbor EVPN-CLIENT send-community extended
   neighbor EVPN-CLIENT route-reflector-client
   neighbor 10.0.0.11 peer group EVPN-CLIENT
   neighbor 10.0.0.12 peer group EVPN-CLIENT
   neighbor 10.0.0.13 peer group EVPN-CLIENT
   neighbor 10.0.0.14 peer group EVPN-CLIENT
   neighbor 10.0.0.15 peer group EVPN-CLIENT
   !
   address-family evpn
      neighbor RR-PEER activate
      neighbor EVPN-CLIENT activate
      exit
   exit
!
ip routing
!
end
```

### leaf1 (10.0.0.11) — ESI-LAG side A toward host1

```
hostname leaf1
!
vrf instance TENANT_A
   exit
!
interface Loopback0
   ip address 10.0.0.11/32
   isis enable UNDERLAY
   isis passive
   exit
!
interface Ethernet1
   description "link-to-spine1"
   no switchport
   ip address 10.1.1.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet2
   description "link-to-spine2"
   no switchport
   ip address 10.2.1.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet3
   description "link-to-host1"
   channel-group 1 mode active
   exit
!
interface Port-Channel1
   switchport access vlan 10
   evpn ethernet-segment
      identifier 0000:0000:0000:1001:0001
      route-target import 00:00:10:01:00:01
      exit
   exit
!
vlan 10
   name TENANT_A_WEB
   exit
!
interface Vlan10
   vrf TENANT_A
   ip address virtual 192.168.10.1/24
   exit
!
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   vxlan vrf TENANT_A vni 50010
   exit
!
router isis UNDERLAY
   net 49.0001.0000.0000.0011.00
   is-type level-2
   log-adjacency-changes
   address-family ipv4 unicast
      exit
   exit
!
router bgp 65000
   router-id 10.0.0.11
   no bgp default ipv4-unicast
   neighbor SPINES peer group
   neighbor SPINES remote-as 65000
   neighbor SPINES update-source Loopback0
   neighbor SPINES send-community extended
   neighbor 10.0.0.21 peer group SPINES
   neighbor 10.0.0.22 peer group SPINES
   !
   address-family evpn
      neighbor SPINES activate
      exit
   !
   vlan 10
      rd 10.0.0.11:10
      route-target both 10:10
      redistribute learned
      exit
   !
   vrf TENANT_A
      rd 10.0.0.11:100
      route-target import evpn 100:100
      route-target export evpn 100:100
      redistribute connected
      exit
   exit
!
ip routing
ip routing vrf TENANT_A
!
end
```

### leaf2 (10.0.0.12) — ESI-LAG side B toward host1

```
hostname leaf2
!
vrf instance TENANT_A
   exit
!
interface Loopback0
   ip address 10.0.0.12/32
   isis enable UNDERLAY
   isis passive
   exit
!
interface Ethernet1
   description "link-to-spine1"
   no switchport
   ip address 10.1.2.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet2
   description "link-to-spine2"
   no switchport
   ip address 10.2.2.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet3
   description "link-to-host1"
   channel-group 1 mode active
   exit
!
interface Port-Channel1
   switchport access vlan 10
   evpn ethernet-segment
      identifier 0000:0000:0000:1001:0001
      route-target import 00:00:10:01:00:01
      exit
   exit
!
vlan 10
   name TENANT_A_WEB
   exit
!
interface Vlan10
   vrf TENANT_A
   ip address virtual 192.168.10.1/24
   exit
!
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   vxlan vrf TENANT_A vni 50010
   exit
!
router isis UNDERLAY
   net 49.0001.0000.0000.0012.00
   is-type level-2
   log-adjacency-changes
   address-family ipv4 unicast
      exit
   exit
!
router bgp 65000
   router-id 10.0.0.12
   no bgp default ipv4-unicast
   neighbor SPINES peer group
   neighbor SPINES remote-as 65000
   neighbor SPINES update-source Loopback0
   neighbor SPINES send-community extended
   neighbor 10.0.0.21 peer group SPINES
   neighbor 10.0.0.22 peer group SPINES
   !
   address-family evpn
      neighbor SPINES activate
      exit
   !
   vlan 10
      rd 10.0.0.12:10
      route-target both 10:10
      redistribute learned
      exit
   !
   vrf TENANT_A
      rd 10.0.0.12:100
      route-target import evpn 100:100
      route-target export evpn 100:100
      redistribute connected
      exit
   exit
!
ip routing
ip routing vrf TENANT_A
!
end
```

### leaf3 (10.0.0.13) — single-homed host2

```
hostname leaf3
!
vrf instance TENANT_A
   exit
!
interface Loopback0
   ip address 10.0.0.13/32
   isis enable UNDERLAY
   isis passive
   exit
!
interface Ethernet1
   description "link-to-spine1"
   no switchport
   ip address 10.1.3.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet2
   description "link-to-spine2"
   no switchport
   ip address 10.2.3.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet3
   description "link-to-host2"
   switchport access vlan 10
   exit
!
vlan 10
   name TENANT_A_WEB
   exit
!
interface Vlan10
   vrf TENANT_A
   ip address virtual 192.168.10.1/24
   exit
!
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   vxlan vrf TENANT_A vni 50010
   exit
!
router isis UNDERLAY
   net 49.0001.0000.0000.0013.00
   is-type level-2
   log-adjacency-changes
   address-family ipv4 unicast
      exit
   exit
!
router bgp 65000
   router-id 10.0.0.13
   no bgp default ipv4-unicast
   neighbor SPINES peer group
   neighbor SPINES remote-as 65000
   neighbor SPINES update-source Loopback0
   neighbor SPINES send-community extended
   neighbor 10.0.0.21 peer group SPINES
   neighbor 10.0.0.22 peer group SPINES
   !
   address-family evpn
      neighbor SPINES activate
      exit
   !
   vlan 10
      rd 10.0.0.13:10
      route-target both 10:10
      redistribute learned
      exit
   !
   vrf TENANT_A
      rd 10.0.0.13:100
      route-target import evpn 100:100
      route-target export evpn 100:100
      redistribute connected
      exit
   exit
!
ip routing
ip routing vrf TENANT_A
!
end
```

### leaf4 (10.0.0.14) — single-homed host3

```
hostname leaf4
!
vrf instance TENANT_A
   exit
!
interface Loopback0
   ip address 10.0.0.14/32
   isis enable UNDERLAY
   isis passive
   exit
!
interface Ethernet1
   description "link-to-spine1"
   no switchport
   ip address 10.1.4.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet2
   description "link-to-spine2"
   no switchport
   ip address 10.2.4.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet3
   description "link-to-host3"
   switchport access vlan 10
   exit
!
vlan 10
   name TENANT_A_WEB
   exit
!
interface Vlan10
   vrf TENANT_A
   ip address virtual 192.168.10.1/24
   exit
!
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   vxlan vrf TENANT_A vni 50010
   exit
!
router isis UNDERLAY
   net 49.0001.0000.0000.0014.00
   is-type level-2
   log-adjacency-changes
   address-family ipv4 unicast
      exit
   exit
!
router bgp 65000
   router-id 10.0.0.14
   no bgp default ipv4-unicast
   neighbor SPINES peer group
   neighbor SPINES remote-as 65000
   neighbor SPINES update-source Loopback0
   neighbor SPINES send-community extended
   neighbor 10.0.0.21 peer group SPINES
   neighbor 10.0.0.22 peer group SPINES
   !
   address-family evpn
      neighbor SPINES activate
      exit
   !
   vlan 10
      rd 10.0.0.14:10
      route-target both 10:10
      redistribute learned
      exit
   !
   vrf TENANT_A
      rd 10.0.0.14:100
      route-target import evpn 100:100
      route-target export evpn 100:100
      redistribute connected
      exit
   exit
!
ip routing
ip routing vrf TENANT_A
!
end
```

### leaf5 (10.0.0.15) — single-homed host4, separate tenant VRF

```
hostname leaf5
!
vrf instance TENANT_B
   exit
!
interface Loopback0
   ip address 10.0.0.15/32
   isis enable UNDERLAY
   isis passive
   exit
!
interface Ethernet1
   description "link-to-spine1"
   no switchport
   ip address 10.1.5.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet2
   description "link-to-spine2"
   no switchport
   ip address 10.2.5.2/30
   isis enable UNDERLAY
   isis network point-to-point
   exit
!
interface Ethernet3
   description "link-to-host4"
   switchport access vlan 20
   exit
!
vlan 20
   name TENANT_B_APP
   exit
!
interface Vlan20
   vrf TENANT_B
   ip address virtual 192.168.20.1/24
   exit
!
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 20 vni 10020
   vxlan vrf TENANT_B vni 50020
   exit
!
router isis UNDERLAY
   net 49.0001.0000.0000.0015.00
   is-type level-2
   log-adjacency-changes
   address-family ipv4 unicast
      exit
   exit
!
router bgp 65000
   router-id 10.0.0.15
   no bgp default ipv4-unicast
   neighbor SPINES peer group
   neighbor SPINES remote-as 65000
   neighbor SPINES update-source Loopback0
   neighbor SPINES send-community extended
   neighbor 10.0.0.21 peer group SPINES
   neighbor 10.0.0.22 peer group SPINES
   !
   address-family evpn
      neighbor SPINES activate
      exit
   !
   vlan 20
      rd 10.0.0.15:20
      route-target both 20:20
      redistribute learned
      exit
   !
   vrf TENANT_B
      rd 10.0.0.15:200
      route-target import evpn 200:200
      route-target export evpn 200:200
      redistribute connected
      exit
   exit
!
ip routing
ip routing vrf TENANT_B
!
end
```

---

## 3. Linux host configs (commands run inside each container)

Run via `docker exec -it clab-ceos-fabric-<node> bash`, then as root:

### host1 — ESI-LAG dual-homed (bond0, LACP active, VLAN10)

```bash
sudo ip link add bond0 type bond mode 802.3ad lacp_rate fast
sudo ip link set eth1 down
sudo ip link set eth1 master bond0
sudo ip link set eth2 down
sudo ip link set eth2 master bond0
sudo ip link set eth1 up
sudo ip link set eth2 up
sudo ip link set bond0 up
sudo ip addr add 192.168.10.31/24 dev bond0
# sudo ip route add default via 192.168.10.1
# Use only if need to test a specific inter-subnet path within the same VRF
sudo ip route add <destination-subnet> via 192.168.10.1 dev bond0
```

### host2 — single-homed to leaf3, VLAN10

```bash
sudo ip addr add 192.168.10.32/24 dev eth1
sudo ip link set eth1 up
# sudo ip route add default via 192.168.10.1
# Use only if need to test a specific inter-subnet path within the same VRF
sudo ip route add <destination-subnet> via 192.168.10.1 dev bond0
```

### host3 — single-homed to leaf4, VLAN10

```bash
sudo ip addr add 192.168.10.33/24 dev eth1
sudo ip link set eth1 up
# sudo ip route add default via 192.168.10.1
# Use only if need to test a specific inter-subnet path within the same VRF
sudo ip route add <destination-subnet> via 192.168.10.1 dev bond0
```

### host4 — single-homed to leaf5, VLAN20 / TENANT_B

```bash
sudo ip addr add 192.168.20.34/24 dev eth1
sudo ip link set eth1 up
# sudo ip route add default via 192.168.20.1
# Use only if need to test a specific inter-subnet path within the same VRF
sudo ip route add <destination-subnet> via 192.168.20.1 dev eth1
```

---

## 4. Validation commands (on the cEOS nodes)

### 4.1 P2P links UP/UP

```
show interfaces description
show interfaces status
```

### 4.2 ISIS underlay

```
show isis interface brief          ! confirm P2P interfaces are "Up"
show isis neighbors                ! adjacency state should show "UP"
show isis database                 ! confirm all 7 system-IDs present
show ip route isis                 ! confirm all loopbacks learned via ISIS
```

### 4.3 Ping to loopbacks (run from any node, sourced from its own Loopback0)

```
ping 10.0.0.21 source Loopback0
ping 10.0.0.22 source Loopback0
ping 10.0.0.11 source Loopback0
ping 10.0.0.12 source Loopback0
ping 10.0.0.13 source Loopback0
ping 10.0.0.14 source Loopback0
ping 10.0.0.15 source Loopback0
```
All should succeed once ISIS has converged — this proves the underlay is
ready to carry the iBGP EVPN sessions.

### 4.4 BGP EVPN overlay

```
show bgp evpn summary                       ! all sessions Established
show bgp evpn route-type imet               ! Type-3 (Inclusive Multicast — VTEP/VNI discovery)
show bgp evpn route-type mac-ip             ! Type-2 (MAC/IP — host reachability)
show bgp evpn route-type ip-prefix ipv4     ! Type-5 (IP-Prefix — subnet routes from redistribute connected)
show bgp evpn instance                      ! per-VNI RD/RT/route counts
```

### 4.5 VXLAN data plane

```
show vxlan vtep                    ! confirm remote VTEP loopbacks discovered
show vxlan address-table           ! MAC-to-VTEP mapping learned via EVPN
show interfaces vxlan1
```

### 4.6 ESI / multihoming (on leaf1 and leaf2)

```
show bgp evpn route-type ethernet-segment
show bgp evpn route-type ethernet-segment detail
show port-channel

# Seeing learned MAC addresses
show mac address-table vlan 10
show bgp evpn route-type mac-ip
show vxlan address-table
```

---

## 5. Host validation (inside each Linux container)

```bash
ip addr show
ip route show

# host1 only — confirm LACP bond is up with both links active
cat /proc/net/bonding/bond0

# host2 -> ping gateway and host2's L2-stretch peer (host3, different leaf, same VNI)
ping -c4 192.168.10.1
ping -c4 192.168.10.33

# host1 -> ping gateway and host2/host3 (proves ESI-LAG host reaches L2-stretched peers)
ping -c4 192.168.10.1
ping -c4 192.168.10.32

# host4 -> ping its own gateway only
ping -c4 192.168.20.1

# Expected to FAIL by design (different VRF, no RT leak — proves tenant isolation):
ping -c4 192.168.10.32
```
