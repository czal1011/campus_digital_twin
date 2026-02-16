#! /usr/bin/env python3

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.log import lg
from mininet.topo import Topo
from mininet.link import TCLink
import os
import random
import time

''' Topology (Grid):
LN1  --  LN2  --  LN3  --  LN4  
 |        |        |        |  
LN5  --  LN6  --  LN7  --  LN8  
 |        |        |        |  
LN9  --  LN10 --  LN11 --   LN12  
 |        |        |        |  
LN13 --  LN14 --   LN15 -- LN16  
'''

'''
For the new topology we use the Ryu network controller that needs to be installed on the system.
The controller is started in a new terminal with the following command:

ryu-manager --observe-links ryu_multipath.py

the ryu_multipath.py is from https://github.com/wildan2711/multipath // https://wildanmsyah.wordpress.com/2018/01/21/testing-ryu-multipath-routing-with-load-balancing-on-mininet/
'''

debug = 0
scenario_time = 72000 # in seconds
stddelay = '2ms'
numberOfClients = 3 # default value
stdQueueSize = 4444 # max queue size is in packets, so 1500 Byte (MTU) * 13333333 = 20 GB
stdbw = 33 # in MBit/s, max 1000 MBit/s

class MyTopo(Topo):
    def __init__(self):
        Topo.__init__(self)


        self.leafs_north = [f'LN{i+1}' for i in range(16)]  # Define 16 leaf switches
        switches = {}

        # Create switches (LN1 to LN16)
        for ln in self.leafs_north:
            switches[ln] = self.addSwitch(ln, switch='ovsk')

        # Connect switches in a 4x4 grid structure
        for i in range(4):
            for j in range(4):
                switch_id = i * 4 + j  # Calculate switch index in the grid

                # Connect switch to its right neighbor (if not at the right edge)
                if j < 3:
                    right_id = switch_id + 1
                    self.addLink(switches[self.leafs_north[switch_id]], 
                                 switches[self.leafs_north[right_id]], 
                                 bw=stdbw, delay=stddelay)

                # Connect switch to its bottom neighbor (if not at the bottom edge)
                if i < 3:
                    down_id = switch_id + 4
                    self.addLink(switches[self.leafs_north[switch_id]], 
                                 switches[self.leafs_north[down_id]], 
                                 bw=stdbw, delay=stddelay)


        def addClient(name, linkedSwitch):
            client = self.addHost(name)
            self.addLink(client, linkedSwitch, bw=stdbw, delay=stddelay)
            return client
        
        # Add static services
        SCC_N1 = addClient('SCC_N1', switches['LN1'])
        CAMPUS_N = addClient('CAMPUS_N', switches['LN2'])
        LSDF = addClient('LSDF', switches['LN3'])
        FILE = addClient('FILE', switches['LN6'])
        SCC_N2 = addClient('SCC_N2', switches['LN9'])
        BWCLOUD = addClient('BWCLOUD', switches['LN14'])




        def addHostsToLeaf(leaf_name, num_hosts):
            for i in range(num_hosts):
                host_name = f"{leaf_name}C{i+1}"
                host = self.addHost(host_name)
                self.addLink(host, switches[leaf_name], bw=stdbw, delay=stddelay)


        # Add Clients
        addHostsToLeaf("LN2", 3)
        addHostsToLeaf("LN9", 3)
        addHostsToLeaf("LN12", 3)

def configure_switches(net):
    """ Sets all switches in Mininet to standalone mode """
    
    print("[+] Configurating switches...")
    for switch in net.switches:
        switch.cmd('ovs-vsctl set-fail-mode {} standalone'.format(switch.name))
        
    # Check with "sudo ovs-vsctl show" in separate terminal!



def configure_servers(net):

    for port in range(5201, 5211):  # 9 ports for each server
        net['SCC_N1'].cmd(f"iperf3 -s -p {port} -V --json > scc_n1.json &")
        net['CAMPUS_N'].cmd(f"iperf3 -s -p {port} -V --json > campus_n.json &")
        net['LSDF'].cmd(f"iperf3 -s -p {port} -V --json > lsdf.json &")
        net['FILE'].cmd(f"iperf3 -s -p {port} -V --json > fileserver.json &")
        net['SCC_N2'].cmd(f"iperf3 -s -p {port} -V --json > scc_n2.json &")
        net['BWCLOUD'].cmd(f"iperf3 -s -p {port} -V --json > bwcloud.json &")

    '''
    Netzwerk Szenarios:
    
    1. Backup-Welle am Abend:
    Jeden Abend gegen 22 Uhr starten automatisierte Backup-Prozesse auf den Endgeräten der  Mitarbeiter. Diese verbinden sich gleichzeitig mit dem zentralen Fileserver der Universität, um wichtige Dokumente und Konfigurationsdateien zu sichern. D.h. alle Clients ---> FILE 
    '''

def scenario_backup(net, numberOfClients):
    
    print(f"[+] Initializing backup...")
    os.system("mkdir -p scenario_backup_folder")
    # To delete the folder use "sudo rm -r scenario_backup_folder"
    
    FILE_ip = "10.0.0.3"
    port = 5201 # default iperf3 port
    
    for j in range(1, numberOfClients + 1):
        clients = [f'LN2C{j}', f'LN9C{j}', f'LN12C{j}'] # Only North Campus!
        
        if debug:
            print(f"[DEBUG] Processing the following clients for iteration {j}: {clients}")
        
        for i in range(min(numberOfClients, len(clients))):
            client = clients[i]
            
            if client in net:  # Check if client exists in the network
                parallel_streams = random.randint(1, 5)  # Random number of parallel connections
                bandwidth = random.choice(["0.625MB", "3.25MB", "9.875MB", "19.75MB", "33MB"]) # Random bandwidth
                
                if debug:
                    print(f"[DEBUG] Starting iperf3 from {client} to FILE server with {parallel_streams} streams and {bandwidth} bandwidth on port {port}...")
                net[client].cmd(f"iperf3 -c 10.0.0.3 -p {port} -P {parallel_streams} -b {bandwidth} -t {scenario_time} -V --json > scenario_backup_folder/backup_results_{client}.json &")
                
                net[client].cmd(f"ping -c {scenario_time} 10.0.0.3 > scenario_backup_folder/ping_backup_results_{client}.txt &")
                
                port = port + 1 # Take the next free port

    
    '''
    2.  Arbeitsalltag
    Während eines typischen Arbeitstages in der Universität greifen verschiedene Nutzer auf unterschiedliche Server zu:
    Studierende verbinden sich mit dem E-Learning-System der Uni, nutzen VPN-Zugänge für Online-Datenbanken oder greifen auf den WLAN-Druckerserver zu. Dozierende und Mitarbeiter laden Vorlesungsmaterialien auf die Webserver hoch oder nutzen Remote-Desktop-Verbindungen, um sich mit Hochleistungsrechnern im Rechenzentrum zu verbinden. Forschende übertragen große Datenmengen zwischen lokalen Arbeitsplätzen und HPC-Clustern für simulationsbasierte Berechnungen. 
    '''
def scenario_normal(net, numberOfClients):

    print(f"[+] Initializing a simulation of an average workday...")
    os.system("mkdir -p scenario_normal_folder")
    # To delete the folder use "sudo rm -r scenario_normal_folder"
    
    port = 5201 # default iperf3 port
    
    # Define the list of servers for North Campus
    north_campus_servers = {
    "SCC_N1": "10.0.0.14", 
    "CAMPUS_N": "10.0.0.2", 
    "LSDF": "10.0.0.13", 
    "FILE": "10.0.0.3", 
    "SCC_N2": "10.0.0.15", 
    "BWCLOUD": "10.0.0.1"
     }

    
    for j in range(1, numberOfClients + 1):
        clients = [f'LN2C{j}', f'LN9C{j}', f'LN12C{j}'] # Only North Campus!
        
        if debug:
            print(f"[DEBUG] Processing the following clients for iteration {j}: {clients}")
        
        for i in range(min(numberOfClients, len(clients))):
            client = clients[i]
            
            if client in net:  # Check if client exists in the network
                # Randomly select the server
                server, server_ip = random.choice(list(north_campus_servers.items()))

                
                # Randomize other parameters
                parallel_streams = random.randint(1, 5)  # Random number of parallel connections
                bandwidth = random.choice(["0.625MB", "3.25MB", "9.875MB", "19.75MB", "33MB"])
                
                if debug:
                    print(f"[DEBUG] Starting iperf3 from {client} to {server} server with {parallel_streams} streams and {bandwidth} bandwidth...")
                
                net[client].cmd(f"iperf3 -c {server_ip} -p {port} -P {parallel_streams} -b {bandwidth} -t {scenario_time} -V --json > scenario_normal_folder/normal_results_{client}.json &")
                
                net[client].cmd(f"ping -c {scenario_time} 10.0.0.3 > scenario_normal_folder/ping_normal_results_{client}.txt &")
                port = port + 1 # Take the next free port
    
    
    '''
    3. Notfall – Netzwerk-Ausfall und Failover-Test (Geht nur bei neuer Topologie weil dynamisch routing)

    In einer Universität ist eine stabile Netzwerkverbindung essenziell, um Vorlesungen, Forschungsarbeiten und Verwaltungsaufgaben sicherzustellen. Doch was passiert, wenn ein zentraler Router oder ein wichtiger Link ausfällt?
    In diesem Szenario wird simuliert, dass ein zentraler Netzwerk-Knoten (z. B. der Haupt-Router im Rechenzentrum) plötzlich ausfällt.
    zB mit "link down" auf einem SDN-Switch einer Route und schauen was passiert.
    '''
def scenario_emergency(net, numberOfClients):

    print(f"[+] Initializing a simulation of an average workday with link failure...")
    os.system("mkdir -p scenario_link_failure_folder")
    
    port = 5201  # Default iperf3 port

    # Define the list of servers for North Campus
    north_campus_servers = {
        "SCC_N1": "10.0.0.14",
        "CAMPUS_N": "10.0.0.2",
        "LSDF": "10.0.0.13",
        "FILE": "10.0.0.3",
        "SCC_N2": "10.0.0.15",
        "BWCLOUD": "10.0.0.1"
    }

    for j in range(1, numberOfClients + 1):
        clients = [f'LN2C{j}', f'LN9C{j}', f'LN12C{j}']  # Only North Campus!

        for i in range(min(numberOfClients, len(clients))):
            client = clients[i]

            if client in net:  # Check if client exists in the network
                server, server_ip = random.choice(list(north_campus_servers.items()))

                parallel_streams = random.randint(1, 5)  # Random number of parallel connections
                bandwidth = random.choice(["0.625MB", "3.25MB", "9.875MB", "19.75MB", "33MB"])

                net[client].cmd(f"iperf3 -c {server_ip} -p {port} -P {parallel_streams} -b {bandwidth} -t {scenario_time} -V --json > scenario_link_failure_folder/fail_results_{client}.json &")
                net[client].cmd(f"ping -c {scenario_time} FILE > scenario_link_failure_folder/ping_fail_results_{client}.txt &")
                
                port += 1  # Take the next free port

    # Warten bis zur Hälfte der Szenariozeit
    time.sleep(scenario_time / 2)
    print("[+] Simulating link failure...")

    # Beispielhafte Link-Failures – passe das an deine Topologie an
    links_to_fail = [("LN5", "LN6"), ("LN6", "LN7"), ("LN7", "LN8")]
    
    for link in links_to_fail:
        node1, node2 = link
        if node1 in net and node2 in net:
            net.configLinkStatus(node1, node2, 'down')
            print(f"[-] Link between {node1} and {node2} is now DOWN!")





class CustomCLI(CLI):
        
    def do_debug(self, arg):
        #Toggle debug mode. Usage: debug 1 (enable) / debug 0 (disable)
        global debug
        if arg.strip() == "1":
            debug = 1
            print("[!] Debug mode enabled.")
        elif arg.strip() == "0":
            debug = 0
            print("[!] Debug mode disabled.")
        else:
            print("[!] Usage: debug 1 (enable) / debug 0 (disable)")

    
    def do_scenario(self, arg):
        """Run a scenario. Usage: scenario 1"""
        if arg.strip() == "1":
            print("[+] Running scenario 'Backup-Welle am Abend'...")
            scenario_backup(self.mn, numberOfClients)
            print(f"[!] Don't terminate until simulation is over...(~{scenario_time}sec)")
            time.sleep(scenario_time+3)
            print("[+] Done.")
        elif arg.strip() == "2":
            print("[+] Running scenario 'Arbeitsalltag'...")
            scenario_normal(self.mn, numberOfClients)
            print(f"[!] Don't terminate until simulation is over...(~{scenario_time}sec)")
            time.sleep(scenario_time+3)
            print("[+] Done.")
        elif arg.strip() == "3":
            print("[+] Running scenario 'Notfall – Netzwerk-Ausfall und Failover-Test'...")
            scenario_emergency(self.mn, numberOfClients) 
              
        else:
            print("[!] Unknown scenario. Usage: scenario [1|2|3]")




def nettopo(**kwargs):
    topo = MyTopo()
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, link=TCLink, **kwargs)
    net.addController('c0', controller=RemoteController, port=6633)
    return net

if __name__ == '__main__':
    lg.setLogLevel('info')
    net = nettopo()
    net.start()
    configure_switches(net)
    configure_servers(net)
    CustomCLI(net)
    net.stop()
