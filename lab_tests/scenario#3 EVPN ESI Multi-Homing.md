#### EVPN ESI Multi-Homming
IS-IS is the underlay routing protocol; its only job is to provide reachability between the physical leaf loopbacks (VTEP IPs) [Inference]. However, IS-IS does not carry tenant MAC addresses or overlay subnets

BGP EVPN is the overlay control plane used to distribute those MACs and tenant IPs.

- About Type-1 Auto-Discovery Per-ES route:
Its sole job is mass-withdrawal: when a multihomed leaf loses its physical link to the dual-homed device, it withdraws this route, and every remote VTEP in the fabric immediately stops using that leaf as a next-hop for every MAC behind that segment.
- About Type-1 Auto-Discovery Per-EVI (Ethernet Virtual Instance) route:
This is the aliasing and load-balancing route. Originated per ESI per VNI. Allows remote VTEPs to ECMP toward both leaf1 and leaf2 for traffic destined to any MAC behind that ESI, even if only one of the two leaves ever originated the Type-2. This is called aliasing.
- MAC Aliasing is the mechanism that ensures remote switches utilize both uplinks to host1, preventing wasted bandwidth.


###### leaf3,leaf4,leaf5 Configuration Strategy

cleanup leaf3,leaf4
```
no interface Vxlan1
no interface Vlan10
router bgp 65000
   no address-family evpn
   no vlan 10
   no vrf TENANT_B
```
cleanup leaf5
```
no interface Vxlan1
no interface Vlan20
router bgp 65000
   no address-family evpn
   no vlan 10
   no vlan 20
   no vrf TENANT_B
```

###### leaf1,leaf2 Configuration Strategy
config leaf1
```
! 1. Data Plane: VRF and VLAN
vlan 10
   name TENANT_B_WEB
!
vrf instance TENANT_B
ip routing vrf TENANT_B
!
interface Vlan10
   vrf TENANT_B
   ip address virtual 192.168.10.1/24

! 2. Data Plane: ESI Multihoming on Port-Channel
interface Port-Channel10
   switchport access vlan 10
   evpn ethernet-segment
      ! ! The higher the preferred
      designated-forwarder election algorithm preference 200
      identifier 0000:0000:0001:0002:0012
      route-target import 00:01:00:02:00:12
   lacp system-id 0000.0001.0012

! 3. Data Plane: VXLAN Overlay
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010

! 4. Control Plane: BGP EVPN
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
   vlan 10
      rd 10.0.0.11:10
      route-target both 10:10
      redistribute learned
   !
   address-family evpn
      neighbor SPINES activate
```
config leaf2
```
! 1. Data Plane: VRF and VLAN
vlan 10
   name TENANT_B_WEB
!
vrf instance TENANT_B
ip routing vrf TENANT_B
!
interface Vlan10
   vrf TENANT_B
   ip address virtual 192.168.10.1/24

! 2. Data Plane: ESI Multihoming on Port-Channel
interface Port-Channel10
   switchport access vlan 10
   evpn ethernet-segment
      designated-forwarder election algorithm preference 100
      identifier 0000:0000:0001:0002:0012
      route-target import 00:01:00:02:00:12
   lacp system-id 0000.0001.0012

! 3. Data Plane: VXLAN Overlay
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010

! 4. Control Plane: BGP EVPN
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
   vlan 10
      rd 10.0.0.12:10
      route-target both 10:10
      redistribute learned
   !
   address-family evpn
      neighbor SPINES activate
```

##### Validation
To observe Type-1 and Type-4 routes, we must look at intra-subnet traffic between host1 and host2 (VLAN 10)
We see both flavors of EVPN Type-1 (Auto-Discovery) routes without any SVIs and without the VRF TENANT_B configured in BGP

1. Look at the Designated Forwarder (DF) election (Type-4 route); Should be leaf1
2. See the Type-1 Auto-Discovery route Per-ES; Just by having the Po10 physically up and has an EVPN ESI configured.
3. See the Type-1 Auto-Discovery route Per-EVI:
```
0 0000:0000:0001:0002:0012
```
The 0 represents the Ethernet Tag ID. In a standard VXLAN VLAN-based service, the Ethernet Tag ID is set to 0.
4. Run a wireshark packet capture on the leaf1 or leaf2 to see both EVPN routes; Filter by bgp.evpn.nlri.rt == 1 or 4
