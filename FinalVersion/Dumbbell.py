#! /usr/bin/env python3
"""
Mininet Dumbbell Topology Experiment
- 3 left hosts (clients):  L1, L2, L3
- 3 right hosts (servers): R1, R2, R3
- Two switches in the middle: s1 -- s2 (bottleneck link)

Measurements:
- iperf3 throughput logged as JSON (per flow)
- ping RTT logged as text (per flow)

Notes:
- This script uses OVS in standalone mode (no controller required).
- Traffic runs via a custom Mininet CLI command:  scenario 1
"""

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSSwitch
from mininet.log import lg
from mininet.topo import Topo
from mininet.link import TCLink

import argparse
import os
import time


class DumbbellTopo(Topo):
    def __init__(self, n_left=3, n_right=3, access_bw=100, access_delay="1ms",
                 access_queue=1000, bottleneck_bw=20, bottleneck_delay="10ms",
                 bottleneck_queue=200, **kwargs):
        super().__init__(**kwargs)

        s1 = self.addSwitch("s1", switch="ovsk")
        s2 = self.addSwitch("s2", switch="ovsk")

        # Bottleneck link (core)
        self.addLink(
            s1, s2,
            bw=bottleneck_bw,
            delay=bottleneck_delay,
            max_queue_size=bottleneck_queue,
            use_htb=True
        )

        # Left access links
        for i in range(1, n_left + 1):
            h = self.addHost(f"L{i}")
            self.addLink(
                h, s1,
                bw=access_bw,
                delay=access_delay,
                max_queue_size=access_queue,
                use_htb=True
            )

        # Right access links
        for i in range(1, n_right + 1):
            h = self.addHost(f"R{i}")
            self.addLink(
                h, s2,
                bw=access_bw,
                delay=access_delay,
                max_queue_size=access_queue,
                use_htb=True
            )


def configure_switches_standalone(net: Mininet) -> None:
    print("[+] Setting OVS fail-mode to standalone...")
    for sw in net.switches:
        sw.cmd(f"ovs-vsctl set-fail-mode {sw.name} standalone")


def start_iperf_servers(net: Mininet, n_right: int, base_port: int, out_dir: str) -> None:
    """
    Starts iperf3 servers on R1..Rn_right.
    One port per server; server logs are stored in out_dir.
    """
    os.makedirs(out_dir, exist_ok=True)
    for i in range(1, n_right + 1):
        host = net[f"R{i}"]
        port = base_port + (i - 1)
        log_path = os.path.join(out_dir, f"iperf3_server_R{i}_p{port}.json")

        # -V verbose, --json output; redirect stdout to file
        # Running in background
        host.cmd(f"iperf3 -s -p {port} -V --json > {log_path} 2>&1 &")
    print(f"[+] iperf3 servers started on ports {base_port}..{base_port + n_right - 1}")


def run_clients_to_servers(
    net: Mininet,
    n_left: int,
    n_right: int,
    base_port: int,
    duration_s: int,
    parallel_streams: int,
    offered_rate: str,
    out_dir: str
) -> None:
    """
    Runs iperf3 clients from L1..Ln_left to R1..Rn_right.
    Mapping used: Li -> R((i-1) mod n_right)+1
    Also runs ping in parallel for RTT logging.
    """
    os.makedirs(out_dir, exist_ok=True)

    for i in range(1, n_left + 1):
        client = net[f"L{i}"]
        server_idx = ((i - 1) % n_right) + 1
        server = net[f"R{server_idx}"]
        server_ip = server.IP()
        port = base_port + (server_idx - 1)

        iperf_log = os.path.join(out_dir, f"iperf3_L{i}_to_R{server_idx}_p{port}.json")
        ping_log = os.path.join(out_dir, f"ping_L{i}_to_R{server_idx}.txt")

        # iperf3:
        # -c <server_ip> client mode
        # -p port
        # -t duration
        # -P parallel streams
        # -b offered rate (TCP: sets target; actual depends on congestion)
        # -V verbose, --json output
        client.cmd(
            f"iperf3 -c {server_ip} -p {port} -t {duration_s} "
            f"-P {parallel_streams} -b {offered_rate} -V --json > {iperf_log} 2>&1 &"
        )

        # ping:
        # One ICMP per second; count == duration_s gives ~duration_s seconds
        client.cmd(f"ping -i 1 -c {duration_s} {server_ip} > {ping_log} 2>&1 &")

    print(f"[+] Started {n_left} client flows (each with ping RTT logging).")


class CustomCLI(CLI):
    def do_scenario(self, arg):
        """
        Run experiment scenarios.
        Usage:
          scenario 1
        """
        args = arg.strip().split()
        if len(args) != 1:
            print("[!] Usage: scenario 1")
            return

        if args[0] == "1":
            cfg = self.mn._exp_cfg
            out_dir = cfg["out_dir"]

            print("[+] Scenario 1: L1..Lk -> R1..Rm traffic + ping RTT logging")
            start_iperf_servers(
                self.mn,
                n_right=cfg["n_right"],
                base_port=cfg["base_port"],
                out_dir=out_dir
            )

            # Small pause to ensure servers are listening
            time.sleep(1)

            run_clients_to_servers(
                self.mn,
                n_left=cfg["n_left"],
                n_right=cfg["n_right"],
                base_port=cfg["base_port"],
                duration_s=cfg["duration_s"],
                parallel_streams=cfg["parallel_streams"],
                offered_rate=cfg["offered_rate"],
                out_dir=out_dir
            )

            print(f"[!] Letting scenario run for {cfg['duration_s']} seconds...")
            time.sleep(cfg["duration_s"] + 2)
            print("[+] Scenario finished. Logs saved in:", out_dir)
        else:
            print("[!] Unknown scenario. Only scenario 1 is implemented.")


def parse_args():
    p = argparse.ArgumentParser(description="Mininet Dumbbell experiment with iperf3+ping logging")

    # Topology size
    p.add_argument("--n-left", type=int, default=3)
    p.add_argument("--n-right", type=int, default=3)

    # Access links
    p.add_argument("--access-bw", type=int, default=100, help="Mbit/s")
    p.add_argument("--access-delay", type=str, default="1ms")
    p.add_argument("--access-queue", type=int, default=1000, help="packets")

    # Bottleneck link
    p.add_argument("--bottleneck-bw", type=int, default=20, help="Mbit/s")
    p.add_argument("--bottleneck-delay", type=str, default="10ms")
    p.add_argument("--bottleneck-queue", type=int, default=200, help="packets")

    # Traffic
    p.add_argument("--duration", type=int, default=60, help="seconds")
    p.add_argument("--parallel", type=int, default=3, help="iperf3 parallel streams (-P)")
    p.add_argument("--rate", type=str, default="50M", help="iperf3 offered rate (-b), e.g., 10M, 0.5G")

    # Logging
    p.add_argument("--out-dir", type=str, default="scenario_dumbbell_folder")
    p.add_argument("--base-port", type=int, default=5201)

    return p.parse_args()


def main():
    args = parse_args()
    lg.setLogLevel("info")

    topo = DumbbellTopo(
        n_left=args.n_left,
        n_right=args.n_right,
        access_bw=args.access_bw,
        access_delay=args.access_delay,
        access_queue=args.access_queue,
        bottleneck_bw=args.bottleneck_bw,
        bottleneck_delay=args.bottleneck_delay,
        bottleneck_queue=args.bottleneck_queue
    )

    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, link=TCLink, autoSetMacs=True)
    net.start()

    try:
        configure_switches_standalone(net)

        # Store experiment config for CLI access
        net._exp_cfg = {
            "n_left": args.n_left,
            "n_right": args.n_right,
            "duration_s": args.duration,
            "parallel_streams": args.parallel,
            "offered_rate": args.rate,
            "out_dir": args.out_dir,
            "base_port": args.base_port,
        }

        print("[+] Network is up.")
        print("[+] Run:  scenario 1")
        print("[+] Then: exit")
        CustomCLI(net)

    finally:
        net.stop()


if __name__ == "__main__":
    main()

