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

def broadcast_user_list():
    """Sends the updated list of connected users to all clients."""
    user_list = ",".join(clients.keys())
    for conn in clients.values():
        try:
            conn.sendall(f"/users {user_list}".encode('utf-8'))
        except Exception as e:
            print(f"Error sending user list: {e}")

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    username = None

    try:
        # Get username stuff
        username = conn.recv(1024).decode('utf-8').strip()
        clients[username] = conn
        print(f"[REGISTERED] {username} connected from {addr}")

        # Announce new user and send updated user list
        announcement = f"*** {username} has joined the chat ***"
        for client_conn in clients.values():
            client_conn.sendall(announcement.encode('utf-8'))
        broadcast_user_list()

        while True:
            msg = conn.recv(1024).decode('utf-8')
            if not msg:
                break

            print(f"[{username}@{addr}] {msg}")

            if msg.startswith("/pm"):
                parts = msg.split()
                if len(parts) >= 3:
                    recipient = parts[1]
                    private_message = " ".join(parts[2:])
                    sender_info = f"(Private) {username}:"
                    if recipient in clients:
                        try:
                            clients[recipient].sendall(f"{sender_info} {private_message}".encode('utf-8'))
                            # Optionally send a confirmation to the sender
                            conn.sendall(f"(Private to {recipient}) {private_message}".encode('utf-8'))
                        except Exception as e:
                            print(f"Error sending private message to {recipient}: {e}")
                    else:
                        conn.sendall(f"User {recipient} not found.".encode('utf-8'))
                else:
                    conn.sendall("Invalid private message format. Use: /pm <username> <message>".encode('utf-8'))
            else:
                # Broadcast to all clients (except the sender)
                for client_username, client_conn in clients.items():
                    if client_username != username:
                        client_conn.sendall(f"{username}: {msg}".encode('utf-8'))

    except Exception as e:
        print(f"Error handling client {addr} ({username}): {e}")
    finally:
        if username in clients:
            # Announce user leaving and send updated user list
            leave_msg = f"*** {username} has left the chat ***"
            del clients[username]
            for client_conn in clients.values():
                client_conn.sendall(leave_msg.encode('utf-8'))
            broadcast_user_list()

        print(f"[DISCONNECT] {addr} ({username}) disconnected.")
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