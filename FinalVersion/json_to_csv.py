# load one client json file (L1<->R1)
# average RTT values for all 5 streams -> output.txt
# use other useful metrics for input.txt
# convert that to csv

import json

folder_name: str = 'scenario_dumbbell_folder'
file_name: str = 'iperf3_L1_to_R1_p5201.json'

out_data = []

# read given json file and extract metrics / collected data
with open(folder_name + '/' + file_name, 'r') as file:
	content: list = json.load(file)['intervals']
		
	for x in content:
		streams: list = x['streams']
		# (re)set sums for in_data & out_data
		rtt_sum = 0
		throughput_sum = 0
		retransmits_sum = 0
		snd_cwnd_sum = 0
		snd_wnd_sum = 0
		rttvar_sum = 0
		# calculate new RTT sum and add the average to out_data
		for flow in streams:
			rtt_sum += flow['rtt']
			throughput_sum += flow['bits_per_second']
			retransmits_sum += flow['retransmits']
			snd_cwnd_sum += flow['snd_cwnd']
			snd_wnd_sum += flow['snd_wnd']
			rttvar_sum += flow['rttvar']
		out_data.append([throughput_sum / 5, retransmits_sum / 5, snd_cwnd_sum / 5, snd_wnd_sum / 5, rttvar_sum / 5, rtt_sum / 5])


with open(folder_name + '/data.csv', 'w', newline='') as csv_out_file:
	csv_out_file.write("throughput,retransmits,snd_cwnd,snd_wnd,rttvar,rtt\n")
	for tup in out_data:
		csv_out_file.write(f"{tup[0]},{tup[1]},{tup[2]},{tup[3]},{tup[4]},{tup[5]}\n")
