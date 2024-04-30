#! /usr/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, OVSController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import lg
from mininet.cli import CLI

"""
1 Controller
2-3 Switches
Server
Client
"""
class SimpleTopo(Topo):
	def __init__(self):
		Topo.__init__(self)
		
		# create switches
		s1 = self.addSwitch('s1')
		s2 = self.addSwitch('s2')
		s3 = self.addSwitch('s3')
		
		# create hosts
		client = self.addHost('client', ip='10.0.0.3/26')
		server = self.addHost('server', ip='10.0.0.18/26')
		
		# link them together
		self.addLink(client, s1)
		self.addLink(server, s3, delay='1000ms', loss=5)
		
		self.addLink(s1, s2)
		self.addLink(s2, s3)
# create topology
def createTopo(**kwargs):
	topo = SimpleTopo()
	return Mininet(topo=topo, link=TCLink, controller=OVSController, **kwargs)

if __name__ == '__main__':
	lg.setLogLevel('info')
	net = createTopo()
	net.start()
	CLI(net)
	net.stop()