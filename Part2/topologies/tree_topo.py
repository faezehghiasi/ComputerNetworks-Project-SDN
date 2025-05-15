# topologies/tree_topo.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mininet.topo import Topo
import math

class TreeTopoCustom(Topo):
    def build(self, depth=2, fanout=2):
        def add_tree_node(level, parent=None, count=[1]):
            if level > depth:
                return
            sw = self.addSwitch('s{}'.format(count[0]))
            count[0] += 1
            if parent:
                self.addLink(sw, parent)
            for i in range(fanout):
                if level == depth:
                    h = self.addHost('h{}'.format(count[0]))
                    count[0] += 1
                    self.addLink(h, sw)
                else:
                    add_tree_node(level + 1, sw, count)

        add_tree_node(1)

topos = {"tree": TreeTopoCustom}

