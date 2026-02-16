from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, OVSController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import lg
from mininet.clean import cleanup
from mininet.cli import CLI
from datetime import datetime
from multiprocessing import Process
import argparse
import csv
import time

# program arguments
log_level = "info"
scenario = 1
packets = 0
iperfTest = False
cli = False
size = 56
timeout = "5"

# global access
net = None
results = [] # results from the ping and iperf tests, for the CSV files
snd = [0, 0, 0] # send counters
rcv = [0, 0, 0] # receive counters

# parse program arguments (sudo python3 ./dumbbell.py ARGUMENTS)
# -l: log level for the mininet logger
# -s: scenario / behavior of the middle link
# -p: amount of packets to send in a ping test. Setting this to 0 disables the ping test.
# -i: perform an iperf test
# -c: launch a CLI (after the tests)
def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("-c", "--count", "--packets", default=5, help="How many packets should be sent through the bottleneck link per ping pair during a ping test. Setting this to 0 disables the ping test.")
	parser.add_argument("--cli", default=False, action='store_true', help="If a CLI should be opened up.")
	parser.add_argument("--iperf", "--iperfTest", default=False, action='store_true', help="If an Iperf UDP test should be performed.")
	parser.add_argument("-l", "--log-level",default="info", help="Log level used by the Mininet logger.")
	parser.add_argument("-s", "--size", default=56, help="Size of the packets sent between hosts")
	parser.add_argument("--scenario", default=1, help="The behavior (scenario) used by the middle bottleneck link (s1 <-> s2).")
	parser.add_argument("-t", "--timeout", default="5", help="Time to wait for a response from the ping command in the ping test.")
	parser.add_argument("-m", "--multipleFlows", default=False, action='store_true', help="If flows from h2 to h5 and h3 to h6 should exist.")
	
	return parser.parse_args()


# Dumbbell topology class: 2 switches, each with 3 distinct hosts.
# The behavior of the middle link (so far packet loss rate & bandwidth)
# depends on the scenario.
class DumbbellTopo(Topo):
	def __init__(self):
		Topo.__init__(self)
				
		r1 = self.addSwitch('r1')
		r2 = self.addSwitch('r2')
		
		# create hosts
		h1 = self.addHost('h1', ip='10.0.0.1/24')
		h2 = self.addHost('h2', ip='10.0.0.2/24')
		h3 = self.addHost('h3', ip='10.0.0.3/24')
		h4 = self.addHost('h4', ip='10.0.0.4/24')
		h5 = self.addHost('h5', ip='10.0.0.5/24')
		h6 = self.addHost('h6', ip='10.0.0.6/24')
		
		# link them together
		self.addLink(h1, r1, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h2, r1, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h3, r1, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h4, r2, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h5, r2, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		self.addLink(h6, r2, bw=100, delay='20ms', max_queue_size=100, use_htb=True)
		
		self.addLink(r1, r2, bw=1, delay='50ms', loss=0, max_queue_size=100, use_htb=True)
		
		
# Create and return the dumbbell topology.
# [Param] controller: Controller to use for the Mininet instance.
# [Returns] Mininet based on the dumbbell topology.
def create_topo(controller, **kwargs):
	topo = DumbbellTopo()
	return Mininet(topo=topo, link=TCLink, controller=controller, **kwargs)

	
def send_data(net, packet_size, multiple_flows=False):
	net['h4'].cmd('iperf3 -s &')
	net['h5'].cmd('iperf3 -s &')
	net['h6'].cmd('iperf3 -s &')
		
	if multiple_flows:
		iperf_cl_h1 = Process(target=iperf,args=(client:=net['h1'], server:=net['h4']))
		iperf_cl_h2 = Process(target=iperf,args=(client:=net['h2'], server:=net['h5']))
		iperf_cl_h3 = Process(target=iperf,args=(client:=net['h3'], server:=net['h6']))
		iperf_cl_h1.start()
		iperf_cl_h2.start()
		iperf_cl_h3.start()
		
		time.sleep(15)
		
		iperf_cl_h1.join()
		iperf_cl_h2.join()
		iperf_cl_h3.join()
	else:
		iperf_cl_h1 = Process(target=iperf,args=(client:=net['h1'], server:=net['h4']))
		iperf_cl_h1.start()
		
		time.sleep(15)
		
		iperf_cl_h1.join()
		

def iperf(client, server):
	timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	client.cmd(f'iperf3 -u -c {server.IP()} > {timestamp}_iperf_{client.name}.out')
	# https://stackoverflow.com/questions/7207309/how-to-run-functions-in-parallel


if __name__ == '__main__':
	args = parse_args()
	
	cleanup()
	
	c = OVSController("c1") # create controller
	net = create_topo(c, listenPort=6654) # create Mininet (incl. topology)
	
	net.start() # start the Mininet instance
	
	send_data(net, 56, args.multipleFlows)
		
	CLI(net)
	
	#time.sleep(30)
	
	print("\n### Stopping Mininet...\n")
	net.stop()
	
	print(str(results))
