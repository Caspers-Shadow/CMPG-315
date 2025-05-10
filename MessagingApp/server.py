#!/usr/bin/env python3
# server.py
import socket
import threading

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 12345
clients = {}  # key = username, value = socket

def get_local_ip():
    """Get the local IP address of the server"""
    try:
        # Create a temporary socket to determine the local IP
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_socket.connect(("8.8.8.8", 80))  # Connect to Google's DNS
        local_ip = temp_socket.getsockname()[0]
        temp_socket.close()
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "127.0.0.1"  # Return localhost if failed

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
    local_ip = get_local_ip()
    print(f"[STARTING] Server is starting")
    print(f"[LOCAL IP] Share this with clients on your network: {local_ip}")
    print(f"[NOTE] Clients should use this IP: {local_ip} in their connection code")
    
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