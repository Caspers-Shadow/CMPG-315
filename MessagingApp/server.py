#!/usr/bin/env python3
# server.py
import socket
import threading
import requests  # Added missing import

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 12345
clients = {}  # key = username, value = socket

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text  # Fixed URL format
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return "Could not retrieve public IP"

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    username = None
    
    try:
        # Get username stuff
        username = conn.recv(1024).decode('utf-8').strip()
        clients[username] = conn
        print(f"[REGISTERED] {username} connected from {addr}")
        
        # Announce new user
        announcement = f"*** {username} has joined the chat ***"
        for client_conn in clients.values():
            if client_conn != conn:  # Don't send to the new user
                client_conn.sendall(announcement.encode('utf-8'))
   
        while True:
            msg = conn.recv(1024).decode('utf-8')
            if not msg:
                break
            print(f"[{addr}] {msg}")
            # Broadcast to all clients
            for client_conn in clients.values():
                client_conn.sendall(msg.encode('utf-8'))
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        if username in clients:
            # Announce user leaving
            leave_msg = f"*** {username} has left the chat ***"
            del clients[username]
            for client_conn in clients.values():
                client_conn.sendall(leave_msg.encode('utf-8'))
                
        print(f"[DISCONNECT] {addr} disconnected.")
        conn.close()
       
def start_server():
    public_ip = get_public_ip()
    print(f"[STARTING] Server is starting")
    print(f"[PUBLIC IP] Share this with clients: {public_ip}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reuse of address
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Server is listening on port {PORT}")
   
    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True  # Make thread exit when main thread exits
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        except Exception as e:
            print(f"Error accepting connection: {e}")
       
if __name__ == "__main__":
    start_server()