#!/usr/bin/env python3

# client.py
import socket
import threading

SERVER_IP = '127.0.0.1'  # Die is net sodat ek con toets ons moet n actuall ip dink ek kry
PORT = 12345

def receive_messages(sock):
	while True:
		try:
			msg = sock.recv(1024).decode('utf-8')
			print(f"[MESSAGE] {msg}")
		except:
			print("[ERROR] Connection lost.")
			break
		
def start_client():
	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client.connect((SERVER_IP, PORT))
	print("[CONNECTED] You are now connected to the server.")
	
	threading.Thread(target=receive_messages, args=(client,), daemon=True).start()
	
	while True:
		msg = input()
		client.sendall(msg.encode('utf-8'))
		
if __name__ == "__main__":
	start_client()
	