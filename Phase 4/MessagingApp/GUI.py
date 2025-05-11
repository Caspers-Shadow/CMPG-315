import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
import urllib.request

PORT = 12345

def get_public_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org').read().decode()
    except:
        return None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

class ChatApp:
    def __init__(self, root, is_server, server_ip=None):
        self.root = root
        self.root.title("Chat App")

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled')
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.entry = tk.Entry(root)
        self.entry.pack(padx=10, pady=(0, 10), fill=tk.X)
        self.entry.bind("<Return>", self.send_message)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if is_server:
            self.start_server()
        else:
            self.connect_to_server(server_ip)

    def start_server(self):
        self.clients = []
        try:
            self.socket.bind(('', PORT))
            self.socket.listen()
            public_ip = get_public_ip() or get_local_ip()
            self.append_text(f"Server started.\nYour public IP: {public_ip}\nWaiting for clients on port {PORT}...")
            threading.Thread(target=self.accept_clients, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Server Error", f"Could not start server:\n{e}")
            self.root.destroy()

    def accept_clients(self):
        while True:
            client, addr = self.socket.accept()
            self.clients.append(client)
            self.append_text(f"[Connected] {addr}")
            threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()

    def handle_client(self, client):
        try:
            while True:
                msg = client.recv(1024).decode()
                if not msg:
                    break
                self.append_text(f"[Client]: {msg}")
                for c in self.clients:
                    if c != client:
                        c.send(msg.encode())
        except:
            self.append_text("A client disconnected.")
        finally:
            client.close()

    def connect_to_server(self, ip):
        try:
            self.socket.connect((ip, PORT))
            self.append_text(f"Connected to server at {ip}:{PORT}")
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Could not connect to {ip}:{PORT}\n{e}")
            self.root.destroy()

    def receive_messages(self):
        while True:
            try:
                msg = self.socket.recv(1024).decode()
                if msg:
                    self.append_text(f"[Server]: {msg}")
            except:
                break

    def send_message(self, event=None):
        msg = self.entry.get()
        if not msg:
            return
        self.append_text(f"[You]: {msg}")
        self.entry.delete(0, tk.END)
        try:
            self.socket.send(msg.encode())
        except:
            for c in getattr(self, "clients", []):
                try:
                    c.send(msg.encode())
                except:
                    pass

    def append_text(self, msg):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, msg + '\n')
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

def main():
    root = tk.Tk()
    root.withdraw()

    public_ip = get_public_ip()
    local_ip = get_local_ip()

    choice = messagebox.askquestion("Choose Mode", "Do you want to start as Server? (Click 'No' to connect as Client)")
    if choice == 'yes':
        root.deiconify()
        ChatApp(root, is_server=True)
    else:
        default_ip = public_ip or local_ip or "127.0.0.1"
        server_ip = simpledialog.askstring("Server IP", f"Enter Server IP:", initialvalue=default_ip)
        if server_ip:
            root.deiconify()
            ChatApp(root, is_server=False, server_ip=server_ip)
        else:
            root.destroy()

    root.mainloop()

if __name__ == "__main__":
    main()
