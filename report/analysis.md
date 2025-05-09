# Part 1 – Single Topology Analysis

## Topology
- One switch (s1)
- 7 hosts (h1–h7)
- Each host is directly connected to the switch

## CLI Output Summary
- `nodes`: lists all devices
- `net`: shows links and interface names
- `links`: confirms each host is connected and link status is OK
- `dump`: shows IP addresses and PIDs
- `pingall`: all hosts are reachable (0% dropped)

## Link Failure Test
- Disabled link: `link h1 s1 down`
- Observed: h1 could not reach others; others could communicate normally
- After `link h1 s1 up`, full connectivity restored

## Why is the network diameter always 2 in Single topology?

In a single-switch (star) topology:
- All hosts connect directly to one switch.
- So, communication from host A to host B always goes:
  A → Switch → B = 2 hops
→ Therefore, diameter = 2 (maximum path length).

## Why does Linear topology have larger diameter?

In a Linear topology:
- Hosts are connected in a chain through switches.
- Host A to host Z may go through multiple hops:
  A → s1 → B → s2 → C → s3 → D ...
→ Diameter increases as the number of hops grows.

