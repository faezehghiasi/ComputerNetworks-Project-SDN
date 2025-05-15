#!/usr/bin/env python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.link import TCLink
import os

class TorusTopo(Topo):
    def build(self, rows=2, cols=2):
        sw = {}
        for r in range(rows):
            for c in range(cols):
                s = self.addSwitch('s{}{}'.format(r, c))
                h = self.addHost('h{}{}'.format(r, c))
                self.addLink(h, s)
                sw[(r, c)] = s
        for r in range(rows):
            for c in range(cols):
                self.addLink(sw[(r, c)], sw[(r, (c + 1) % cols)])
                self.addLink(sw[(r, c)], sw[((r + 1) % rows, c)])

topos = {'torus': TorusTopo}

if __name__ == '__main__':
    topo = TorusTopo(rows=2, cols=2)
    net = Mininet(topo=topo, link=TCLink, autoSetMacs=True, autoStaticArp=True)
    net.start()
    for s in net.switches:
        s.cmd('ovs-vsctl set Bridge {} stp_enable=true'.format(s.name))
    net.waitConnected(timeout=5)
    CLI(net)
    net.stop()
    os.system('mn -c')

