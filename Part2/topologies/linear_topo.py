# topologies/linear_topo.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mininet.topo import Topo

class LinearTopoCustom(Topo):
    def build(self, n=5):
        last_switch = None
        for i in range(1, n + 1):
            host = self.addHost('h{}'.format(i))
            switch = self.addSwitch('s{}'.format(i))
            self.addLink(host, switch)
            if last_switch:
                self.addLink(switch, last_switch)
            last_switch = switch

topos = {"linear": LinearTopoCustom}

