import socket
import time
import argparse

snd = 0
packet_size = 56
global sock

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("-i", "--ip", help="IP address to use.")
	parser.add_argument("-p", "--port", help="Port to use.")
	return parser.parse_args()

def generate_packet(packet_size):
	return ("A" * packet_size).encode('UTF-8')

def send():
	global snd
	packet = generate_packet(packet_size)
	while True:
		sock.send(packet)
		snd += 1
		print('[C] Sent packet ' + str(snd))
		time.sleep(1)
	
def close():
	sock.close()

if __name__ == '__main__':
	global sock
	
	args = parse_args()
	ip = args.ip
	port = int(args.port)
	
	print('[C] Starting client...')
	print(f'[C] IP = {ip}, Port = {port}')
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((ip, port))
	print('[C] Client ready to send data')
	send()
