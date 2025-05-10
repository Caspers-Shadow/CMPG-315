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

        announcement = f"*** {username} has joined the chat ***"
        broadcast(announcement, exclude=conn)

        while True:
            msg = conn.recv(1024).decode('utf-8')
            if not msg:
                break

            print(f"[{username}] {msg}")

            if msg.startswith("@"):
                try:
                    target, content = msg[1:].split(":", 1)
                    target = target.strip()
                    content = content.strip()
                    if target in clients:
                        clients[target].sendall(f"[Private] {username}: {content}".encode('utf-8'))
                    else:
                        conn.sendall(f"User '{target}' not found.".encode('utf-8'))
                except ValueError:
                    conn.sendall("Invalid format. Use @username: message".encode('utf-8'))
            else:
                broadcast(msg)

    except Exception as e:
        print(f"[ERROR] {username} | {e}")
    finally:
        if username and username in clients:
            del clients[username]
            leave_msg = f"*** {username} has left the chat ***"
            broadcast(leave_msg)
        conn.close()
        print(f"[DISCONNECT] {addr} disconnected.")

def broadcast(message, exclude=None):
    for user_conn in clients.values():
        if user_conn != exclude:
            try:
                user_conn.sendall(message.encode('utf-8'))
            except:
                pass

def start_server():
    ip = get_local_ip()
    print(f"[STARTING] Server running at {ip}:{PORT}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()