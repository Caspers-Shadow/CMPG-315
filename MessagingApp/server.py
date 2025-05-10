#!/usr/bin/env python3
# server.py
import socket
import threading

HOST = '0.0.0.0'
PORT = 12345
clients = {}  # username: connection

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    username = None
    try:
        username = conn.recv(1024).decode('utf-8').strip()
        if username in clients:
            conn.sendall(f"Username {username} already taken.".encode('utf-8'))
            conn.close()
            return
            
        clients[username] = conn
        print(f"[REGISTERED] {username} connected from {addr}")
        
        # Send list of active users to new client
        send_user_list(conn)
        
        # Announce new user
        announcement = f"*** {username} has joined the chat ***"
        broadcast(announcement, exclude=conn)
        
        # Update all clients with new user list
        update_all_users()
        
        while True:
            msg = conn.recv(1024).decode('utf-8')
            if not msg:
                break
                
            print(f"[{username}] {msg}")
            
            # Check for private message format: @username: message
            if msg.startswith("@"):
                try:
                    # Split at the first colon
                    parts = msg.split(":", 1)
                    if len(parts) != 2:
                        conn.sendall("Invalid format. Use @username: message".encode('utf-8'))
                        continue
                        
                    target = parts[0][1:].strip()  # Remove the @ and whitespace
                    content = parts[1].strip()
                    
                    if target in clients:
                        # Send to target
                        private_msg = f"[Private from {username}] {content}"
                        clients[target].sendall(private_msg.encode('utf-8'))
                        
                        # Send confirmation to sender
                        confirmation = f"[Private to {target}] {content}"
                        conn.sendall(confirmation.encode('utf-8'))
                    else:
                        conn.sendall(f"User '{target}' not found.".encode('utf-8'))
                except Exception as e:
                    print(f"Private message error: {e}")
                    conn.sendall("Error processing private message.".encode('utf-8'))
            else:
                # Normal broadcast message
                broadcast(msg)
    except Exception as e:
        print(f"[ERROR] {username} | {e}")
    finally:
        if username and username in clients:
            del clients[username]
            leave_msg = f"*** {username} has left the chat ***"
            broadcast(leave_msg)
            update_all_users()  # Update user lists after someone leaves
        conn.close()
        print(f"[DISCONNECT] {addr} disconnected.")

def send_user_list(conn):
    """Send list of active users to a specific client"""
    users = ",".join(clients.keys())
    msg = f"/users {users}"
    try:
        conn.sendall(msg.encode('utf-8'))
    except Exception as e:
        print(f"Error sending user list: {e}")

def update_all_users():
    """Send updated user list to all clients"""
    for conn in clients.values():
        send_user_list(conn)

def broadcast(message, exclude=None):
    """Send message to all clients except excluded one"""
    for user_conn in clients.values():
        if user_conn != exclude:
            try:
                user_conn.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Broadcast error: {e}")

def start_server():
    ip = get_local_ip()
    print(f"[STARTING] Server running at {ip}:{PORT}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reuse of address
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Server is listening on port {PORT}")
    print(f"[INFO] Clients should connect to {ip}:{PORT}")
    
    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        except Exception as e:
            print(f"Error accepting connection: {e}")

if __name__ == "__main__":
    start_server()