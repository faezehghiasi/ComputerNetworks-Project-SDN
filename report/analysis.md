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

## Why Diameter = 2?
- All communication passes through a central switch
- Path: host A → switch → host B → exactly 2 hops

