# ESI-LAG / EVPN Multihoming — Study Dialogue
Speakers: PRIYA (guiding, more experienced) and MARCUS (learning, asks the questions you'd actually ask)

---

PRIYA: Okay, so today we're doing a walkthrough of the piece of your lab you just finished — host1, dual-homed into leaf1 and leaf2, using EVPN's ESI-LAG. You've never configured this before, so let's really build it from the ground up. By the end of this, you should be able to explain it cold in an interview.

MARCUS: Perfect, because right now if someone asked me "what is ESI-LAG" I'd probably just say "the multihoming thing" and hope they don't ask a follow-up.

PRIYA: That's exactly the gap we're closing. Let's start with the problem it solves, before we even look at config. Picture host1. It's a single physical or virtual server. In a normal, boring network, that server has one cable, into one switch. If that switch dies, or that link dies, the server's offline. So for anything that matters — and in a real data center, that's most things — you want the server connected to two separate switches.

MARCUS: Right, redundancy. But why is that hard? Isn't that just... plugging in two cables?

PRIYA: It's plugging in two cables, but then you've got a problem: from the server's point of view, and from the network's point of view, how do you use both links at once without creating a loop? If leaf1 and leaf2 both think they independently own this host, you can get duplicate frames, or a broadcast storm, or asymmetric forwarding that breaks connectivity in weird ways.

MARCUS: Okay, so that's where spanning tree would normally come in.

PRIYA: Traditionally, yes — spanning tree blocks one of the links to prevent the loop. But then you're paying for two links and only using one. That's the whole reason technologies like Cisco's vPC, or Arista's MLAG, exist — they let two switches coordinate over a dedicated link between them, called a peer-link, so they can both appear as a single logical switch to the server. The server bonds its two links into one LACP port-channel, and it never even knows it's talking to two different physical boxes.

MARCUS: Right, we talked about MLAG a while back. So is ESI-LAG just Arista's name for the same thing?

PRIYA: This is the key distinction, and it's a great interview answer if you get this right: no. MLAG needs that dedicated peer-link between the two switches, and it's fundamentally a two-switch-only mechanism. ESI-LAG is the EVPN-native way of solving the exact same problem, but it does the coordination entirely through BGP, over the existing fabric — no dedicated peer-link required. And because it's BGP-based, it's not limited to two switches. You could multihome a device to three or four leaves if you needed to.

MARCUS: So in our lab, leaf1 and leaf2 aren't directly wired to each other at all.

PRIYA: Correct — look at the topology. There's no leaf1-to-leaf2 cable anywhere. Everything they coordinate, they coordinate over BGP EVPN, riding on top of the same ISIS underlay and iBGP sessions we already built for the rest of the fabric. That's the elegant part. We didn't add any new plumbing to make this multihoming feature work — we're reusing the exact same control plane.

MARCUS: Okay, so walk me through what we actually configured, because I typed it, but I want to make sure I understand every line.

PRIYA: Let's do it piece by piece. On leaf1, Ethernet3 — the physical port toward host1 — gets one command: channel-group 1 mode active. That's just standard LACP, bundling that physical port into a logical Port-Channel1. Nothing EVPN-specific yet.

MARCUS: Right, that part felt familiar, that's just normal link aggregation.

PRIYA: Exactly. The EVPN part is what we put inside Port-Channel1 itself. Two lines: "evpn ethernet-segment", then under that, "identifier", followed by a ten-byte value — in our case, 0000:0000:0000:1001:0001.

MARCUS: And that value has to match on leaf2 too, right? That tripped me up at first.

PRIYA: That's the single most important thing to get right, and it's a great thing to say explicitly in an interview: the ESI — Ethernet Segment Identifier — has to be configured identically on every leaf that's part of the same segment. That identical value is literally what tells the fabric "these two separate ports, on two separate boxes, are actually the same logical attachment point." If you typo it, or if leaf2 has a different value, EVPN will treat them as two completely unrelated segments, and multihoming breaks silently — you won't get an error, you'll just get behavior that doesn't make sense.

MARCUS: That's a good failure mode to know about for troubleshooting.

PRIYA: Definitely. Okay, second line under ethernet-segment: route-target import, and then a value formatted like a MAC address — 00:00:10:01:00:01 in our config. This one's worth dwelling on because we actually got this wrong on the first pass.

MARCUS: Yeah, I remember — I typed something like 1001:1, and it flat out rejected it with "invalid input."

PRIYA: Right, and the reason is worth understanding, not just memorizing. Route-targets like 10:10 or 100:100, the ones we use for VLANs and VRFs elsewhere in this config — those are the classic BGP extended-community format, AS-number colon number. But this specific route-target, the ES-import route-target, is defined by the EVPN standard, RFC 7432, as a MAC-address-shaped value. It's what leaf1 and leaf2 use to import each other's Type-4 route for this segment. Different route type, different required format.

MARCUS: So if someone asks me in an interview "what format is the ES-import route-target," the answer is literally "it looks like a MAC address, not an AS-colon-number."

PRIYA: Exactly, and bonus point if you can say why — it's derived from, or matched against, the upper six bytes of the nine-byte ESI value itself. It's not arbitrary.

MARCUS: Got it. And on the host side — that's just a Linux bond, right? Nothing EVPN-aware there at all?

PRIYA: Right, and that's actually a nice thing to point out — the host doesn't know or care that this is EVPN underneath. From host1's perspective, it just sees two LACP-capable links and bundles them into bond0, mode 802.3ad. As far as that server's concerned, it's plugged into one switch with two cables. All the cleverness is entirely on the network side.

MARCUS: Okay, so now that it's configured — how do I actually prove it's working? Because "I typed the commands and nothing errored" isn't exactly a strong interview answer.

PRIYA: Good instinct. Let's go through the validation in the order I'd actually do it. First: is the LACP bundle even up. On leaf1, "show port-channel summary." You want to see Port-Channel1 with Ethernet3 as an active, bundled member — not "individual," not "down." If LACP itself isn't happy, nothing above it matters.

MARCUS: Makes sense, bottom layer first.

PRIYA: Second, we check the EVPN control plane specifically. The command is "show bgp evpn route-type ethernet-segment esi", then the ESI value, then "detail." That shows you the Type-4 route for this segment — critically, it should list both leaf1 and leaf2 as PEs advertising into this same ESI, and it'll show you the result of DF election.

MARCUS: DF being designated forwarder — the one that "wins" for broadcast traffic?

PRIYA: Exactly. In an active-active setup like ours, both leaves can forward known unicast traffic to and from the host, but only one of them — the DF — handles broadcast, unknown-unicast, and multicast traffic toward the segment. That prevents the host from getting duplicate copies of, say, an ARP broadcast, once from leaf1 and once from leaf2.

MARCUS: So I should expect to see leaf1 as DF and leaf2 as non-DF, or vice versa, not both saying they're DF.

PRIYA: Right, and if you ever see both claiming DF, or neither, that's your sign something's misconfigured — usually a mismatched ESI, which loops back to that first point.

MARCUS: Okay, what's next after confirming DF election?

PRIYA: Third, look at the MAC table itself — "show mac address-table vlan 10" on both leaf1 and leaf2. Here's the specific thing to check, and it's a great one to mention explicitly in an interview because it's the actual proof of multihoming: host1's MAC address should appear as a local entry on both leaves, pointing at Port-Channel1 — not local on one and learned-via-VXLAN on the other. If it showed up as VXLAN-remote on one of them, that would mean only one leaf actually has a working path to the host, and the other is just hearing about it secondhand through the fabric.

MARCUS: That's a really concrete thing to check. Local on both, not local-plus-remote.

PRIYA: Exactly. Fourth, the control-plane equivalent of that same check — "show bgp evpn route-type mac-ip." You're looking for host1's MAC advertised with the ESI field populated with our actual ESI value, not all-zeros. All-zeros there means EVPN sees it as a single-homed MAC, which tells you the ethernet-segment association isn't actually being applied to that route.

MARCUS: And then, I assume, just... ping?

PRIYA: Right, the simplest test of all, but do it deliberately — from host1, ping host2 and host3, which sit on leaf3 and leaf4 in the same VLAN and subnet. That proves the whole path end to end: LACP up, ESI multihoming working, VXLAN encapsulation across the fabric, and the anycast gateway all functioning together.

MARCUS: Is there a way to actually test the failover, not just that it's configured for it?

PRIYA: Great question, and this is honestly the test I'd be most impressed to hear a candidate describe unprompted. Shut Ethernet3 on whichever leaf is currently the DF — just "shutdown" on that interface. Two things should happen. First, on the remaining leaf, DF election should re-run, and it becomes the new DF, since it's now the only PE left advertising into that ESI. Second — and this is the part that shows you understand EVPN's fast-convergence story — you should see a near-immediate withdrawal of that leaf's Type-1 route, which triggers mass-withdrawal on remote VTEPs, so they redirect traffic toward the surviving leaf without waiting on normal MAC aging timers. Then, importantly, host1 should still be pingable the whole time, with maybe one or two dropped packets during reconvergence, not a sustained outage.

MARCUS: That's a genuinely satisfying test to actually watch happen.

PRIYA: It is, and I'd encourage you to actually run it before your interview, not just read about it, because being able to describe what you personally observed carries a lot more weight than reciting the theory.

MARCUS: Okay, let's talk about the interview framing directly. If someone just asks me cold, "tell me about EVPN multihoming," what's the structure of a good answer?

PRIYA: I'd structure it in four moves. One — state the problem: a device needs redundant links to two switches, without a loop, and ideally using both links actively. Two — name the mechanism: ESI, the Ethernet Segment Identifier, configured identically across all participating leaves, which is what defines the logical segment. Three — say what it enables: DF election so BUM traffic isn't duplicated, split-horizon filtering, and fast convergence through mass-withdrawal if a leaf fails. Four — and this is the move that separates a good answer from a great one — contrast it against MLAG or vPC on your own, without being asked. Say something like "unlike MLAG, this needs no dedicated peer-link between the two switches, and it's not capped at two — it's coordinated entirely through BGP as part of the existing fabric control plane."

MARCUS: That last part feels like the thing that shows I actually understand it, not just memorized it.

PRIYA: Exactly right. And if they push further and ask "what would you check first if a dual-homed host had asymmetric connectivity" — meaning it works through one leaf but not the other — walk them through the same order we just used: LACP bundle status, then the Type-4 ES route and DF state, then the MAC table for local-versus-remote on each leaf, then the Type-2 route's ESI field. That ordered, bottom-up troubleshooting instinct is honestly worth more in an interview than being able to recite the RFC.

MARCUS: One thing I want to make sure I don't fumble — if they ask why we didn't just use MLAG here instead, since this is a lab and either would technically work.

PRIYA: Good one to prep for. Fair answer: in a pure EVPN-VXLAN fabric, ESI-LAG is generally the more modern, standards-based choice specifically because it avoids the peer-link dependency — that peer-link in MLAG is a piece of dedicated infrastructure and a potential failure point that ESI-LAG simply doesn't need. That said, it's fair to acknowledge MLAG is still extremely common in existing deployments, and plenty of production fabrics run MLAG on the access-facing side even with an EVPN-VXLAN core — so it's not that one is universally correct, it's that ESI-LAG is the better architectural fit specifically for an EVPN-native design like this one.

MARCUS: That feels like a nicely balanced answer, not just "ESI good, MLAG bad."

PRIYA: Right, and interviewers tend to notice when you avoid absolutist answers on things that are genuinely trade-offs. Okay — let's close the loop. Give me the one-sentence summary, like you're saying it to close out the topic in an interview.

MARCUS: Host1 is dual-homed to leaf1 and leaf2 using EVPN's ESI-LAG — an identical Ethernet Segment Identifier on both leaves tells the fabric these two ports are one logical segment, they coordinate DF election and fast failover entirely through BGP without needing a dedicated peer-link the way MLAG would, and I validated it by checking LACP status, the Type-4 route, the MAC table showing host1 as local on both leaves, and by actually shutting one leaf's port and watching the other take over DF and keep the host reachable.

PRIYA: That's it. That's an answer that shows you didn't just configure it, you understood it, and you tested it. That's exactly what you want walking into this interview.

MARCUS: Before we move on, can I throw a couple of harder follow-ups at you? The kind that might come after that clean summary, just so I'm not caught flat-footed.

PRIYA: Please. That's exactly how these interviews go — you give the polished answer, and then they poke at it.

MARCUS: Okay. What happens if DF election flaps — like, keeps flipping back and forth between leaf1 and leaf2?

PRIYA: Good one. In practice that usually points to instability in the underlying BGP session or the ISIS underlay, not the ESI feature itself — remember, DF election depends on both leaves reliably seeing each other's Type-4 route. If that session is bouncing, flapping, or hitting some MTU or timer mismatch, you'll see DF ownership bounce along with it. So the answer isn't "go fix ESI," it's "go check BGP EVPN session stability first," the same way we debugged the RR-PEER session earlier in this whole project. It's a good example of how these features are layered — the multihoming logic is only as stable as the control plane underneath it.

MARCUS: That's a nice callback, actually — ties back to all the BGP troubleshooting we already did.

PRIYA: Exactly, and interviewers like seeing that you understand the layering, not just each feature in isolation. Next one?

MARCUS: What's split-horizon actually protecting against here, concretely? I can say the word but I couldn't defend it if pushed.

PRIYA: Fair, let's make it concrete. Say a broadcast frame from some other host arrives at leaf1 from across the VXLAN fabric — it originated somewhere else in the network, not from host1. Leaf1 floods it out to host1, since that's a normal local port. Now, without split-horizon, leaf2 — which also has a link into that same segment — might also try to flood that same frame back out toward host1, or worse, back into the fabric, creating a loop or a duplicate delivery. Split-horizon is the rule that says "a frame that arrived from the fabric, destined for this Ethernet Segment, only gets forwarded out by the DF, and the non-DF suppresses it." It's doing the job spanning-tree blocking used to do, but scoped precisely to this one segment instead of blocking an entire link.

MARCUS: Okay, that's a much sharper explanation than what I had in my head, which was basically just "it stops loops," full stop.

PRIYA: That vague version is fine as a first sentence, but always be ready to make it concrete with a specific frame's journey like we just did — that's usually what separates someone who read the RFC summary from someone who's actually pictured the packet flow.

MARCUS: Last one — how does this actually interact with the VXLAN encapsulation and the anycast gateway we set up? Are those three features — ESI, VXLAN, anycast gateway — fighting for the same job, or do they stack cleanly?

PRIYA: They stack cleanly, and honestly, that layering is one of the more elegant things about this whole design. VXLAN's job is purely to get a frame from one VTEP to another across the underlay — it doesn't know or care about multihoming at all. The anycast gateway's job is to let host1 use the same default-gateway IP and MAC no matter which leaf it's actually plugged into, so routing works identically regardless of physical attachment. ESI-LAG's job is narrower still — it's purely about "which of these two identical-looking attachment points should actively forward this particular frame." None of the three needs to know how the others work. VXLAN encapsulates, anycast gateway makes the L3 hop location-independent, and ESI decides who's allowed to originate or accept L2 traffic on this specific segment at this specific moment. Three separate, composable jobs.

MARCUS: That's a genuinely satisfying way to think about it — like each layer solves exactly one problem and trusts the others to solve theirs.

PRIYA: That's the EVPN philosophy in a sentence, honestly. If you can say that in an interview, you're not just describing a feature, you're describing an architecture.

MARCUS: Alright, I feel a lot more solid on this now. Let's go make it actually happen on leaf3, leaf4, and leaf5 next.

PRIYA: One host-facing lab section down. Let's keep going.
