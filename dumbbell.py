from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, OVSController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import lg
from mininet.cli import CLI
from mininet.examples.multipoll import monitorFiles
from datetime import datetime

class DumbbellTopo(Topo):
	def __init__(self):
		Topo.__init__(self)
		
		# create switches
		s1 = self.addSwitch('s1')
		s2 = self.addSwitch('s2')
		
		# create hosts
		
		h1 = self.addHost('h1', ip='10.0.0.1')
		h2 = self.addHost('h2', ip='10.0.0.2')
		h3 = self.addHost('h3', ip='10.0.0.3')
		h4 = self.addHost('h4', ip='10.0.0.4')
		h5 = self.addHost('h5', ip='10.0.0.5')
		h6 = self.addHost('h6', ip='10.0.0.6')
		
		# link them together
		self.addLink(h1, s1, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h2, s1, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h3, s1, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h4, s2, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h5, s2, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h6, s2, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		
		# scenarios
		#self.addLink(s1, s2, bw=10, delay='50ms', max_queue_size=100, use_htb=True)
		self.addLink(s1, s2, bw=10, delay='50ms', loss=30, max_queue_size=100, use_htb=True)
		
# create Topology
def createTopo(controller, **kwargs):
	topo = DumbbellTopo()
	return Mininet(topo=topo, link=TCLink, controller=controller, **kwargs)


def monitorHosts(controller, time=10, packetsize=56, **netkwargs):
	topo = DumbbellTopo()
	net = Mininet(topo=topo, link=TCLink, controller=controller, listenPort=6654, **netkwargs)
	net.start()
	hosts = net.hosts
	outfiles, errfiles = {}, {}
	
	dt = datetime.now().strftime('%Y%m%d_%H%M%S')
	
	outfiles['h1'] = f'./out/h1_{dt}.out'
	errfiles['h1'] = f'./out/h1_{dt}.err'
	net['h1'].cmd('echo >', outfiles['h1'])
	net['h1'].cmd('echo >', errfiles['h1'])
	
	outfiles['h2'] = f'./out/h2_{dt}.out'
	errfiles['h2'] = f'./out/h2_{dt}.err'
	net['h2'].cmd('echo >', outfiles['h2'])
	net['h2'].cmd('echo >', errfiles['h2'])
	
	outfiles['h3'] = f'./out/h3_{dt}.out'
	errfiles['h3'] = f'./out/h3_{dt}.err'
	net['h3'].cmd('echo >', outfiles['h3'])
	net['h3'].cmd('echo >', errfiles['h3'])
		
	net['h1'].cmdPrint(f'ping -v -c 30 -s {packetsize}', net['h4'].IP(), '>', outfiles['h1'], '2>', errfiles['h1'], '&')
	net['h2'].cmdPrint(f'ping -v -c 30 -s {packetsize}', net['h5'].IP(), '>', outfiles['h2'], '2>', errfiles['h2'], '&')
	net['h3'].cmdPrint(f'ping -v -c 30 -s {packetsize}', net['h6'].IP(), '>', outfiles['h3'], '2>', errfiles['h3'], '&')
	
	print(f"Monitoring output for {time} seconds...")
	for h, line in monitorFiles(outfiles, time+1, timeoutms=500):
		if h:
			print(f"[{h}], {line}")
	for h in hosts:
		h.cmd('kill %ping')
	#CLI(net)	
	net.stop()
	
#def ping(net):

if __name__ == '__main__':
	c = OVSController("c1")
	lg.setLogLevel('info')
	
	monitorHosts(controller=c, time=30, packetsize=1432)
	#net = createTopo(c, listenPort=6654)
	#net.start()
	
	#print("\n### Stopping Mininet...\n")
	#net.stop()