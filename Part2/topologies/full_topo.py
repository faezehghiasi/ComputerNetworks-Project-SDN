#!/usr/bin/env python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.link import TCLink
import itertools, os

class FullMeshTopo(Topo):
    def build(self, n=4):
        switches = []
        for i in range(n):
            s = self.addSwitch('s{}'.format(i + 1))
            h = self.addHost('h{}'.format(i + 1))
            self.addLink(h, s)
            switches.append(s)
        for s1, s2 in itertools.combinations(switches, 2):
            self.addLink(s1, s2)

topos = {'full': FullMeshTopo}

if __name__ == '__main__':
    topo = FullMeshTopo(n=4)
    net = Mininet(topo=topo, link=TCLink, autoSetMacs=True, autoStaticArp=True)
    net.start()
    for s in net.switches:
        s.cmd('ovs-vsctl set Bridge {} stp_enable=true'.format(s.name))
    net.waitConnected(timeout=5)
    CLI(net)
    net.stop()
    os.system('mn -c')

