### Flood-and-learn practice
- We don't need the spines to run BGP or act as Route-Reflectors for Flood-and-Learn.
- In pure Flood-and-Learn over VXLAN with static Head-End Replication (HER), MAC address discovery happens strictly in the data plane when packets traverse the network. HER goes without EVPN control plane. VXLAN is purely an Encapsulation / Data Plane Protocol.
- Flood-and-Learn using static VXLAN
- There is NO Overlay Control Plane: Because there is no protocol (like BGP) exchanging MAC addresses prior to host communication, we say that Flood-and-Learn operates with no overlay control plane. The underlay IP routing protocol (like IS-IS in your topology) provides IP reachability between VTEPs, but the overlay MAC table is built dynamically via data-plane flooding.

#### If we choose not to run VXLAN, EVPN, or ESI, MAC learning in a Data Center fabric defaults to traditional mechanisms:

- Data-Plane Flood-and-Learn over Physical L2 (Standard Spanning-Tree): Traditional Layer 2 switching where leaves and spines perform standard bridge-domain MAC learning by inspecting the inner source MAC address of incoming Ethernet frames. This requires running Spanning-Tree Protocol (STP) across the CLOS fabric to block redundant loops.

#### Unknown Unicast Flooding Across the VXLAN Fabric (step-by-step)
```
# 1. Flash ARP table on Linux hosts and leaves
sudo ip neigh flush all
clear mac address-table dynamic

# 2. Inject a broadcast frame on host2 to host3
On host2, inject a unicast frame toward host3's MAC address directly without triggering an ARP request (e.g., using ping 192.168.10.33) and stop.

# 3. Clear the MAC Table on leaf3, flush all learned MAC entries
clear mac address-table dynamic

# 4. Re-send the ping and observe the Flooding Behavior:

Because leaf3 has host2's frame with a known destination IP but an unknown destination MAC in its Layer 2 forwarding table, leaf3 cannot perform head-end unicast forwarding. Instead, leaf3 encapsulates the frame into VXLAN and floods it as unknown unicast to all VTEPs defined in its vxlan vlan 10 flood vtep list (10.0.0.14 and 10.0.0.15).

We should see that leaf3 performed Ingress Replication and duplicated the unicast frame to multiple VTEPs in its Type 3 flood list (10.0.0.15 and 10.0.0.14) is the direct proof that leaf3 had an unknown destination MAC and flooded the packet.
```

#### host2, host3 and host4. We move host4 into VLAN10 for this scenario.

##### Step 1: Flood-and-Learn Host Configuration Strategy

host2,host3,host4 - They sit on the same L2 subnet across three distinct VTEPs.

config example host2
```
sudo ln -sf /usr/share/zoneinfo/Europe/Warsaw /etc/localtime
sudo ip addr add 192.168.10.32/24 dev eth1
sudo ip link set eth1 up
```

###### leaf3,leaf4,leaf5 Configuration Strategy

cleanup leaves
```
no ip routing vrf TENANT_A
no vrf instance TENANT_A
no interface Vlan10

no ip routing vrf TENANT_B
no vrf instance TENANT_B
no interface Vlan20
```

leaf3 configuration
```
hostname leaf3
clock timezone Europe/warsaw
!
vlan 10
   name TENANT_A_WEB
   exit
!
interface Ethernet3
   description "link-to-host2"
   switchport access vlan 10
   exit
!
! Arista EOS software and hardware architecture natively support only one logical VXLAN interface per switch (hard-coded as Vxlan1)
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   ! L2VNI mapping
   vxlan vlan 10 vni 10010
   ! VTEP pointing to leaf3 and leaf4 (static vxlan)
   vxlan vlan 10 flood vtep 10.0.0.14 10.0.0.15
   exit
!
end
```

leaf4 configuration
```
hostname leaf4
clock timezone Europe/warsaw
!
vlan 10
   name TENANT_A_WEB
!
interface Ethernet3
   description link-to-host3
   switchport access vlan 10
!
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   vxlan vlan 10 flood vtep 10.0.0.13 10.0.0.15
   exit
!
end
```

leaf5 configuration (moving host4 to VLAN 10)
```
hostname leaf5
clock timezone Europe/warsaw
!
vlan 10
   name TENANT_A_WEB
!
interface Ethernet3
   description link-to-host4
   switchport mode trunk
   switchport trunk allowed vlan 10,20
!
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   vxlan vlan 10 flood vtep 10.0.0.13 10.0.0.14
   exit
!
end
```


###### host2,host3,host4 Configuration Strategy
host2 (single-homed to leaf3, VLAN 10)
```
sudo ln -sf /usr/share/zoneinfo/Europe/Warsaw /etc/localtime
sudo ip addr add 192.168.10.32/24 dev eth1
sudo ip link set eth1 up
```
host3 (single-homed to leaf4, VLAN 10)
```
sudo ln -sf /usr/share/zoneinfo/Europe/Warsaw /etc/localtime
sudo ip addr add 192.168.10.33/24 dev eth1
sudo ip link set eth1 up
```
host4 (single-homed to leaf5, VLAN 10)
```
sudo ln -sf /usr/share/zoneinfo/Europe/Warsaw /etc/localtime
sudo ip addr add 192.168.10.34/24 dev eth1
sudo ip link set eth1 up
```

##### Mechanics ping from host2 to host4 or host3
host2 broadcasts an ARP request. leaf3 encapsulates it into VXLAN and sends a copy to both leaf4 and leaf5. leaf4 or leaf5 decapsulates the packet, learns host2's MAC dynamically from the inner frame header, and forwards the frame out Ethernet3 to host3 or host4. Check:
show mac address-table
show vxlan address-table
