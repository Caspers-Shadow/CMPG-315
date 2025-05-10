#!/usr/bin/env python3

# server.py
import socket
import threading

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 12345

clients = {} #key = username, value = socket

def get_public_ip():
	try: 
		return requests.get('https//api.ipify.org').text
	except:
		return "Could not retrieve public IP"

def handle_client(conn, addr):

	print(f"[NEW CONNECTION] {addr} connected.")

	try:
	#Get username stuff
		username = conn.recv(1024).decode('utf-8').strip()
		clients[username] = conn
		print(f"[REGISTERED] {username}	connected from {addr}")
	
		while True:
			msg = conn.recv(1024).decode('utf-8')
			if not msg:
				break
			print(f"[{addr}] {msg}")
			# Broadcast to all clients
			for client_conn in clients.values():
				client_conn.sendall(msg.encode('utf-8'))
	except:
		pass
	finally:
		if username in clients:
			del clients[username]
		print(f"[DISCONNECT] {addr} disconnected.")
		conn.close()
		
def start_server():
	public_ip = get_public_ip()
	print(f"[STARTING] Server is starting")
	print(f"[PUBLIC IP] Share this with clients: {public_ip}")

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((HOST, PORT))
	server.listen()
	print(f"[LISTENING] Server is listening on port {PORT}")
	
	while True:
		conn, addr = server.accept()
		thread = threading.Thread(target=handle_client, args=(conn, addr))
		thread.start()
		
if __name__ == "__main__":
	start_server()
	