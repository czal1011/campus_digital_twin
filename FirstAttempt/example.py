#! /usr/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, OVSController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import lg
from mininet.cli import CLI

import sys

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
		self.addLink(server, s3)
		
		self.addLink(s1, s2)
		self.addLink(s2, s3)


# create topology
def createTopo(sdn_controller, **kwargs):
	topo = SimpleTopo()
	return Mininet(topo=topo, link=TCLink, controller=sdn_controller, **kwargs)

def modifyTopo(net):
	s2 = net.get('s2')
	# adding Peter
	peter = net.addHost('peter', ip='10.0.0.10/26')
	net.addLink(peter, 's2')
	s2.attach('s2-eth3')
	peter.cmdPrint('ifconfig peter-eth0 10.0.0.10')
	
def dumpNodeIPandMAC(net):
	c = net['controller'] # controller
	print(f"Controller IP/Port: {c.ip}:{c.port}")
	print(f"Hosts ({len(net.hosts)}):")
	for host in net.hosts:
		print(f"> Name: {host}, IP: {host.IP()}, MAC: {host.MAC()}, Usable Ports: ", end='')
		for port in host.ports:
			print(f"{port}", end='')
		print() # new line

def dumpFlows(controller, cliClosed):
	if cliClosed is False:
		print("Dumping flows before opening CLI...")
	else:
		print("CLI closed, dumping flows...")
	c.cmdPrint("dpctl dump-flows tcp:localhost:6654")
	print("-----------------------------------------------------")
	c.cmdPrint(f"ovs-ofctl dump-flows s1")
	print("Dumping complete, starting CLI...\n",
		  "=====================================================")

if __name__ == '__main__':
	argv = sys.argv # get extra parameters
	
	c = OVSController("controller")
	lg.setLogLevel('info')
	net = createTopo(c, listenPort=6654)
	net.start()
	# print("Testing bandwidth between client and server (iperf)")
	# net.iperf(net.get("client", "server"))
	# print("iperf test done, starting CLI")
	dumpNodeIPandMAC(net)
	
	print("Adding another node...")
	modifyTopo(net)
	
	print(f"s2 Interfaces:")
	net.get('s2').cmdPrint('ifconfig')
	
	dumpFlows(c, cliClosed = False)
	
	if(len(argv) > 1 and argv[1] == '--blockPeter'):
		net.get('s2').cmdPrint('ovs-ofctl add-flow s2 nw_dst=10.0.0.10,actions=drop') # block Peter
	
	CLI(net)
	
	dumpFlows(c, cliClosed = True)
	
	print("\n### Stopping Mininet...\n")
	net.stop()
