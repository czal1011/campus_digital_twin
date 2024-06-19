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
		self.addLink(server, s3)
		
		self.addLink(s1, s2)
		self.addLink(s2, s3)


# create topology
def createTopo(sdn_controller, **kwargs):
	topo = SimpleTopo()
	return Mininet(topo=topo, link=TCLink, controller=sdn_controller, **kwargs)

def modifyTopo(net):
	topo = net.topo
	peter = topo.addHost('peter', ip='10.0.0.10')
	topo.addLink(peter, 's2')

if __name__ == '__main__':
	c = OVSController("controller")
	lg.setLogLevel('info')
	net = createTopo(c, listenPort=6654)
	net.start()
	# print("Testing bandwidth between client and server (iperf)")
	# net.iperf(net.get("client", "server"))
	# print("iperf test done, starting CLI")
	print(f"Controller IP/Port: {c.ip}:{c.port}")
	print(f"Hosts ({len(net.hosts)}):")
	for host in net.hosts:
		print(f"> Name: {host}, IP: {host.IP()}, MAC: {host.MAC()}, Usable Ports: ", end='')
		for port in host.ports:
			print(f"{port}", end='')
		print() # new line
	#CLI(net)
	print("CLI closed, dumping flows...")
	c.cmdPrint(f"dpctl dump-flows tcp:localhost:6654")

	print("Adding another node...")
	peter = net.topo.addHost('peter', ip='10.0.0.10')
	net.topo.addLink(peter, 's2')
	CLI(net)
	
	print("\n### Stopping Mininet...\n")
	net.stop()