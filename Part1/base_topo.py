from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
import argparse

class SingleSwitchTopo(Topo):
    def build(self, n=2):
        switch = self.addSwitch('s1')
        for i in range(1, n + 1):
            host = self.addHost('h{}'.format(i))  # <-- fixed for Python < 3.6
            self.addLink(host, switch)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hosts', type=int, default=2)
    args = parser.parse_args()

    topo = SingleSwitchTopo(n=args.hosts)
    net = Mininet(topo=topo)
    net.start()
    CLI(net)
    net.stop()

