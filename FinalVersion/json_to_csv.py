# load one client json file (L1<->R1)
# average RTT values for all 5 streams -> output.txt
# use other useful metrics for input.txt
# convert that to csv

import json
import csv

folder_name: str = 'scenario_dumbbell_folder (copy)'
file_name: str = 'iperf3_L1_to_R1_p5201.json'

out_data = []
in_data = {'throughput': [],'retransmits': [], 'snd_cwnd': [], 'bandwidth': []}

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
		# calculate new RTT sum and add the average to out_data
		for flow in streams:
			rtt_sum += flow['rtt']
			throughput_sum += flow['bits_per_second']
			retransmits_sum += flow['retransmits']
			snd_cwnd_sum += flow['snd_cwnd']
		out_data.append(rtt_sum / 5)
		in_data['throughput'].append(str(throughput_sum / 5))
		in_data['retransmits'].append(str(retransmits_sum / 5))
		in_data['snd_cwnd'].append(str(snd_cwnd_sum / 5))
		in_data['bandwidth'].append("10000000")


with open(folder_name + '/output.txt', 'w', newline='') as csv_out_file:
	wr = csv.writer(csv_out_file, quoting=csv.QUOTE_ALL)
	wr.writerow(out_data)

# convert in_data to a series of strings
in_data['throughput'] = ', '.join(in_data['throughput'])
in_data['retransmits'] = ', '.join(in_data['retransmits'])
in_data['snd_cwnd'] = ', '.join(in_data['snd_cwnd'])
in_data['bandwidth'] = ', '.join(in_data['bandwidth'])

with open(folder_name + '/input.txt', 'w', newline='') as csv_in_file:
	wr = csv.writer(csv_in_file)
	wr.writerow(in_data.keys())
	wr.writerow(in_data.values())
