# topologies/minimal_topo.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mininet.topo import Topo

class MinimalTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        self.addLink(h1, s1)
        self.addLink(h2, s1)

topos = {"minimal": MinimalTopo}

