from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, OVSController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import lg
from mininet.clean import cleanup
from mininet.cli import CLI
from datetime import datetime
import argparse
import csv
import re
import asyncio

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
	
	return parser.parse_args()

# Dumbbell topology class: 2 switches, each with 3 distinct hosts.
# The behavior of the middle link (so far packet loss rate & bandwidth)
# depends on the scenario.
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
		match scenario:
			case 2: # very small bandwidth with no loss
				self.addLink(s1, s2, bw=0.8, delay='50ms', loss=0, max_queue_size=100, use_htb=True)
			case 3: # similar to the above but even smaller bandwidth
				self.addLink(s1, s2, bw=0.2, delay='50ms', loss=0, max_queue_size=100, use_htb=True)
			case _: # default case (1), no queue congestion but small packet loss rate
				self.addLink(s1, s2, bw=10, delay='50ms', loss=3, max_queue_size=100, use_htb=True)
		
# Create and return the dumbbell topology.
# [Param] controller: Controller to use for the Mininet instance.
# [Returns] Mininet based on the dumbbell topology.
def create_topo(controller, **kwargs):
	topo = DumbbellTopo()
	return Mininet(topo=topo, link=TCLink, controller=controller, **kwargs)

# Custom ping function based on Mininet's Mininet.ping() (net.py) function,
# supporting a custom count / amount and size of the packets as well as a custom timeout.
# [Param] hosts: Hosts to send packets between. Every host sends packets to every other host.
# [Param] count: Amount of packets to send between hosts.
# [Param] size: Size of the packets sent between hosts.
# [Param] timeout: How long to wait for a response. Has to be formatted as a string.
# [Returns] Tuple containing, in order, (1) the packet loss rate, (2) smallest RTT for a ping, (3) average RTT, (4) largest RTT and (5) standard deviation for the RTT.
def ping(hosts=None, count=1, size=56, timeout=None):
	# initialize returned data (and packet counters)
	ping_result = {}
	ploss, rtt_min, rtt_avg, rtt_max, rtt_mdev = 0, 0, 0, 0, 0
	for node in hosts:
		for dest in hosts:
			if node != dest:
				opts = ''
				if timeout:
					opts = f'-W {timeout}'
				if dest.intfs:
					result = node.cmdPrint(f'LANG=C ping -c {count} -s {size} {opts} {dest.IP()}')
					print(result)
					ping_result[node] = parsePing(result)
	return ping_result

# Parses the result of the ping command and extracts packet and RTT data.
# [Param] ping_output: Output of a ping command.
# [Returns] See ping.
def parsePing(ping_output):
	# network unreachable, no packets could be received
	if 'connect: Network is unreachable' in ping_output:
		return 1, 0, 0, 0, 0
	# packets have been received
	# search for amount of transmitted & received packets
	print(ping_output)
	regex = r'(\d+)% packet loss'
	m = re.search( regex, ping_output )
	if m is None:
		print( '*** Error: could not parse ping output: %s\n' %
			   ping_output )
		return 1, 0, 0, 0, 0
	ploss = float(m.group(1)) / 100.0
	# get RTT data
	rtt_regex = r'rtt min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms'
	rtt_stats = re.search(rtt_regex, ping_output)
	if rtt_stats is None:
		print(f'*** Error: could not parse ping output: {ping_output}\n')
		return (1, 0, 0, 0, 0)
	rtt_min = float(rtt_stats.group(1))
	rtt_avg = float(rtt_stats.group(2))
	rtt_max = float(rtt_stats.group(3))
	rtt_mdev = float(rtt_stats.group(4))
	return ploss, rtt_min, rtt_avg, rtt_max, rtt_mdev

# Send packets over the bottleneck link and dump everything into a .txt
# file (containing the raw ping output) and a .csv file (containing
# various types of data about the ping process).
def ping_test():
	global results
	hosts = net.hosts
	
	ping1 = ping(hosts=[net['h1'], net['h4']], count=packets, size=size, timeout=timeout)
	ping2 = ping(hosts=[net['h2'], net['h5']], count=packets, size=size, timeout=timeout)
	ping3 = ping(hosts=[net['h3'], net['h6']], count=packets, size=size, timeout=timeout)
	
	print("====================================")
	print("h1 <-> h4: " + str(ping1))
	print("====================================")
	print("h2 <-> h5: " + str(ping2))
	print("====================================")
	print("h3 <-> h6: " + str(ping3))
	print("====================================")
	
	results.append(ping1[0])
	results.append(ping2[0])
	results.append(ping3[0])
	results.append(ping1[1])
	results.append(ping2[1])
	results.append(ping3[1])
	results.append([size, timeout, packets]) # general data about the ping test: packet size, timeout and amount. All of it will be packed out later
	
	for h in hosts:
		h.cmd('kill %ping')

# perform an Iperf (UDP) test to measure UDP bandwidth
# [Returns] Results of the Iperf test
def iperf():
	print("Performing iperf (UDP) tests...\n")
	iperf_res_udp = {}
	
	iperf_res_udp[0] = net.iperf(hosts=(net['h1'], net['h4']), l4Type='UDP')
	iperf_res_udp[1] = net.iperf(hosts=(net['h2'], net['h5']), l4Type='UDP')
	iperf_res_udp[2] = net.iperf(hosts=(net['h3'], net['h6']), l4Type='UDP')
	return [iperf_res_udp]


def add_dict_entry(counter, ping_output_h1, ping_output_h2, ping_output_h3):
	entry = {}
	entry[time_sec] = counter
	entry[bw_1] = 100
	entry[bw_2] = 100
	entry[bw_3] = 100
	entry[bw_4] = 100
	entry[bw_5] = 100
	entry[bw_6] = 100
	entry[bw_7] = 100
	# add rtt and loss rate
	results.append(entry)
	# add RTT and real packet loss rate, per time_sec, throughput

def convert_results_to_csv():
	timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	with open(f'results_{timestamp}.csv', 'w', newline='') as csvfile:
		fieldnames = [time_sec,bw_1,bw_2,bw_3,bw_4,bw_5,bw_6,bw_7,rtt_1,rtt_2,rtt_3,rtt_4,rtt_5,rtt_6,rtt_7,packet_loss_1,packet_loss_2,packet_loss_3,packet_loss_4,packet_loss_5,packet_loss_6,packet_loss_7]
		writer = csv.DictWriter(csvfile, fieldnames)
		writer.writeheader()
		writer.writerows(results)
	
if __name__ == '__main__':
	args = parse_args()
	lg.setLogLevel(args.log_level)
	cli = args.cli
	iperfTest = args.iperf
	packets = int(args.count)
	size = int(args.size)
	scenario = int(args.scenario)
	timeout = int(args.timeout)
	
	cleanup()
	
	c = OVSController("c1") # create controller
	net = create_topo(c, listenPort=6654) # create Mininet (incl. topology)
	
	net.start() # start the Mininet instance
	
	if packets > 0:
		ping_test() # ping data from one side of the dumbbell to the other, and dump statistics into their own files
	
	if iperfTest == True:
		iperf()
	
	if cli == True:
		CLI(net)
	
	print("\n### Stopping Mininet...\n")
	net.stop()
	
	print(str(results))
