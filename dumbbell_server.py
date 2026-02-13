import socket
import argparse

rcv = 0
packet_size = 56
	
global sock

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("-i", "--ip", help="IP address to use.")
	parser.add_argument("-p", "--port", help="Port to use.")
	parser.add_argument("-t", "--timeout", help="Timeout")
	return parser.parse_args()
	
def receive():
	global rcv
	sock.listen(1)
	while True:
		try:
			(connection, address) = sock.accept()
			while True:
				data = connection.recv(packet_size + 8)
				rcv += 1
				print('[S] Received packet ' + str(rcv))
				if not data:
					break # stop if client stopped
			connection.close()
		except socket.timeout:
			pass

if __name__ == '__main__':
	global sock
	
	args = parse_args()
	ip = args.ip
	port = int(args.port)
	timeout = int(args.timeout)
	
	print('[S] Starting server...')
	print(f'[S] IP = {ip}, Port = {port}, Timeout = {timeout}')
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((ip, port))
	sock.settimeout(timeout)
	print('[S] Server ready to receive data')
	receive()
