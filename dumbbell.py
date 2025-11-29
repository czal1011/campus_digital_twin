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
		self.addLink(s1, s2, bw=10, delay='50ms', loss=3, max_queue_size=100, use_htb=True)
		
# create Topology
def createTopo(controller, **kwargs):
	topo = DumbbellTopo()
	return Mininet(topo=topo, link=TCLink, controller=controller, **kwargs)


def monitorHosts(net, time=10, packetsize=56, **kwargs):
	hosts = net.hosts
	outfiles, errfiles = {}, {}
	
	dt = datetime.now().strftime('%Y%m%d_%H%M%S')
	
	outfilesPath = './out/'
	errfilesPath = './out/err/'
	
	for host in ['h1','h2','h3']:
		outfiles[host] = f'{outfilesPath}{host}_{dt}.out'
		errfiles[host] = f'{errfilesPath}{host}_{dt}.err'
		net[host].cmd('echo >', outfiles[host])
		net[host].cmd('echo >', errfiles[host])
		
	net['h1'].cmdPrint(f'ping -D -a -v -c 30 -s {packetsize}', net['h4'].IP(), '>', outfiles['h1'], '2>', errfiles['h1'], '&')
	net['h2'].cmdPrint(f'ping -D -a -v -c 30 -s {packetsize}', net['h5'].IP(), '>', outfiles['h2'], '2>', errfiles['h2'], '&')
	net['h3'].cmdPrint(f'ping -D -a -v -c 30 -s {packetsize}', net['h6'].IP(), '>', outfiles['h3'], '2>', errfiles['h3'], '&')
	
	print(f"Monitoring output for {time} seconds...")
	for h, line in monitorFiles(outfiles, time+2, timeoutms=500):
		if h:
			print(f"<{h}> {line}")
	
	for h in hosts:
		h.cmd('kill %ping')

if __name__ == '__main__':
	lg.setLogLevel('info')
	
	c = OVSController("c1") # create controller
	net = createTopo(c, listenPort=6654) # create Mininet (incl. topology)
	
	net.start() # start the Mininet
	
	monitorHosts(net=net, time=30, packetsize=32760) # ping data from one side of the dumbbell to the other, and dump statistics into their own files
	
	print("\n### Stopping Mininet...\n")
	net.stop()
