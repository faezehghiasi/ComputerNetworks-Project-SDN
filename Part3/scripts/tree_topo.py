#!/usr/bin/env python3
"""
Tree topology (depth=2, fanout=2) + Traffic control links
Run with:
    sudo mn --custom tree_topo.py --topo mytree --link tc \
            --controller remote,ip=127.0.0.1,port=6633
"""

from mininet.topo import Topo
from mininet.node import OVSSwitch

class MyTree(Topo):
    def build(self, depth=2, fanout=2, bw=100):
        """Recursive tree constructor."""
        def addTree(level, parent):
            if level == depth:
                for i in range(fanout):
                    h = self.addHost("h{}".format(addTree.host_id))
                    addTree.host_id += 1
                    self.addLink(parent, h, bw=bw)
            else:
                for i in range(fanout):
                    s = self.addSwitch("s{}".format(addTree.switch_id),
                                       cls=OVSSwitch,
                                       protocols="OpenFlow13")
                    addTree.switch_id += 1
                    self.addLink(parent, s, bw=bw)
                    addTree(level + 1, s)

        addTree.host_id = 1
        addTree.switch_id = 1
        root = self.addSwitch("s0", cls=OVSSwitch, protocols="OpenFlow13")
        addTree(0, root)

topos = {"mytree": MyTree}

