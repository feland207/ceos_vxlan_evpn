### EVPN (BGP EVPN Overlay)
Control-plane based MAC learning, where MAC/IP bindings are advertised across the fabric using MP-BGP Type-2 routes rather than data-plane flooding.   
We will test:
- The same-subnet L2 extension across host2 (leaf3) and host3 (leaf4); Layer 2 EVPN bridging
- Inter-VRF / inter-subnet L3 routing via Type-5 routes across host1/host2/host3 (TENANT_A) and host4 (TENANT_B on leaf5); Layer 3 EVPN (IP-VRF), we need a Anycast Gateway. For this to work, we must assign an IP address to every Leaf we want to be the 'gateway' for our servers.

#### host2, host3 and host4. We move host4 into VLAN10 for this scenario.

host2,host3,host4 - They sit on the same L2 subnet across three distinct VTEPs; Layer 2 EVPN bridging.
This is usually called L2 EVPN extension.

###### leaf3,leaf4,leaf5 Configuration Strategy
BUM traffic flooding and remote VTEP discovery are now handled automatically by EVPN Type-3 (IMET) route advertisements.
We must remove all manual flood lists (vxlan vlan 10 flood vtep ...)

cleanup leaves
```
no interface Vxlan1
```

leaf3 configuration
```
hostname leaf3
clock timezone Europe/warsaw
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
   ! BGP EVPN control plane
   address-family evpn
      neighbor SPINES activate
      exit
   !
   ! Telling BGP that VLAN 10 should participate in the EVPN overlay
   vlan 10
      rd 10.0.0.13:10
      route-target both 10:10
      redistribute learned
      exit
   !
  !
 !
! 
! Arista EOS software and hardware architecture natively support only one logical VXLAN interface per switch (hard-coded as Vxlan1)
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   exit
!
end
```

leaf4 configuration
```
hostname leaf4
clock timezone Europe/warsaw
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
   ! BGP EVPN control plane
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
  !
 !
! Arista EOS software and hardware architecture natively support only one logical VXLAN interface per switch (hard-coded as Vxlan1)
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   vxlan vlan 10 vni 10010
   exit
!
end
```

leaf5 configuration
```
hostname leaf5
clock timezone Europe/warsaw
!
ip routing vrf TENANT_B
!
! ! Arista EOS requires a global virtual MAC address to initialize the ip address virtual Anycast Gateway feature.
! ! This has nothing to do with the Ethernet Segment Identifier (ESI) 
! ! Can be any valid unicast MAC address, but it must be the exact same across all leaves that share that Anycast Gateway.
ip virtual-router mac-address 00:1c:73:00:00:99
!
vrf instance TENANT_B
   exit
!
vlan 20
   name TENANT_B_APP
   exit
!
! Anycast Gateway SVI
interface Vlan20
   description "Anycast Gateway"
   vrf TENANT_B
   ip address virtual 192.168.20.1/24
   exit
!
interface Ethernet3
   description "link-to-host4"
   switchport mode trunk
   ! host4 port eth1.20
   switchport trunk allowed vlan 20
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
   ! BGP EVPN control plane
   address-family evpn
      neighbor SPINES activate
      exit
   !
   vlan 20
      ! ! RD makes the MAC addresses and Type-3 IMET routes learned in VLAN 20 globally unique
      rd 10.0.0.15:20
      ! ! RT dictates exactly which remote VTEPs will import and export these Layer 2 overlay routes
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
! Arista EOS software and hardware architecture natively support only one logical VXLAN interface per switch (hard-coded as Vxlan1)
interface Vxlan1
   vxlan source-interface Loopback0
   vxlan udp-port 4789
   ! Map VRF to L2VNI 10020; Required for Type-2 (MAC/IP) and Type-3 (IMET) routes
   vxlan vlan 20 vni 10020
   ! Map VRF to L3VNI 50020; Required for Type-5 routes to carry the prefix payload
   vxlan vrf TENANT_B vni 50020
   exit
!
end
```
