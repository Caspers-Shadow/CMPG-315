#!/usr/bin/env python3

# server.py
import socket
import threading

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 12345

clients = []

def handle_client(conn, addr):
	print(f"[NEW CONNECTION] {addr} connected.")
	clients.append(conn)
	
	try:
		while True:
			msg = conn.recv(1024).decode('utf-8')
			if not msg:
				break
			print(f"[{addr}] {msg}")
			# Broadcast to all clients
			for client in clients:
				if client != conn:
					client.sendall(msg.encode('utf-8'))
	except:
		pass
	finally:
		print(f"[DISCONNECT] {addr} disconnected.")
		clients.remove(conn)
		conn.close()
		
def start_server():
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
	