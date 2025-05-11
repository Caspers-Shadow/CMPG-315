
import threading

# ==== SERVER CODE START ====
### Modified Server Code (server.py) ###
import socket
import threading
import time

HOST = '0.0.0.0'
PORT = 12345
BROADCAST_PORT = 12346
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

def broadcast_server_ip():
    """Broadcast server IP periodically for auto-discovery"""
    ip = get_local_ip()
    print(f"[BROADCASTING] Server IP: {ip} on port {BROADCAST_PORT}")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(('', 0))  # Bind to any available port
    
    # Broadcast message format: "CHAT_SERVER:IP:PORT"
    message = f"CHAT_SERVER:{ip}:{PORT}".encode('utf-8')
    
    try:
        while True:
            s.sendto(message, ('<broadcast>', BROADCAST_PORT))
            time.sleep(2)  # Broadcast every 2 seconds
    except Exception as e:
        print(f"[ERROR] Broadcasting stopped: {e}")
    finally:
        s.close()

def handle_client(conn, addr):
    # Rest of your handle_client function remains the same
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
    
    # Start broadcasting server IP for auto-discovery
    broadcast_thread = threading.Thread(target=broadcast_server_ip, daemon=True)
    broadcast_thread.start()
    
    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 2}")  # -2 for main and broadcast threads
        except Exception as e:
            print(f"Error accepting connection: {e}")


# ==== SERVER CODE END ====

# ==== START SERVER THREAD ====
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# ==== GUI CODE START ====
### Modified Client Code (client.py) ###
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox, ttk
import threading
import socket
from collections import defaultdict
import time

class ClientClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Chat Client")
        
        self.server_ip = None
        self.server_port = 12345
        self.broadcast_port = 12346
        
        # Create a frame for connection options
        self.connect_frame = tk.Frame(master)
        self.connect_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(self.connect_frame, text="Chat Client", font=("Arial", 16, "bold")).pack(pady=(0, 20))
        
        # Create connection options
        self.connection_var = tk.StringVar(value="auto")
        
        tk.Radiobutton(
            self.connect_frame, 
            text="Auto-discover server",
            variable=self.connection_var,
            value="auto",
            command=self.toggle_connect_options
        ).pack(anchor=tk.W, pady=5)
        
        tk.Radiobutton(
            self.connect_frame, 
            text="Connect to specific IP", 
            variable=self.connection_var, 
            value="manual",
            command=self.toggle_connect_options
        ).pack(anchor=tk.W, pady=5)
        
        # IP input frame
        self.ip_frame = tk.Frame(self.connect_frame)
        self.ip_frame.pack(fill='x', pady=5)
        
        tk.Label(self.ip_frame, text="Server IP:").pack(side='left')
        self.ip_entry = tk.Entry(self.ip_frame, width=15)
        self.ip_entry.pack(side='left', padx=5)
        self.ip_entry.insert(0, "192.168.0.26")  # Default IP
        self.ip_entry.config(state='disabled')  # Disabled by default when auto is selected
        
        # Status message for auto-discovery
        self.status_label = tk.Label(self.connect_frame, text="", font=("Arial", 10))
        self.status_label.pack(pady=10)
        
        # Connect button
        self.connect_button = tk.Button(self.connect_frame, text="Connect", command=self.start_connection)
        self.connect_button.pack(pady=10)
        
        # Server discovery progress
        self.progress = ttk.Progressbar(self.connect_frame, orient="horizontal", length=300, mode="indeterminate")
        
        # Discovered servers list
        self.servers_frame = tk.Frame(self.connect_frame)
        self.servers_label = tk.Label(self.servers_frame, text="Discovered Servers:")
        self.servers_label.pack(anchor=tk.W)
        self.servers_listbox = tk.Listbox(self.servers_frame, height=5, width=40)
        self.servers_listbox.pack(fill='both', expand=True)
        
        # Store discovered servers
        self.discovered_servers = {}  # {display_name: (ip, port)}
        
        # Auto-discover as default
        self.toggle_connect_options()
        
    def toggle_connect_options(self):
        mode = self.connection_var.get()
        if mode == "auto":
            self.ip_entry.config(state='disabled')
            self.status_label.config(text="Will auto-discover servers on the network")
            self.servers_frame.pack(fill='both', expand=True, pady=10)
            self.start_auto_discovery()
        else:
            self.ip_entry.config(state='normal')
            self.status_label.config(text="Enter server IP address manually")
            self.servers_frame.pack_forget()
            self.stop_auto_discovery()
    
    def start_auto_discovery(self):
        """Start auto-discovery of chat servers"""
        self.discovery_active = True
        self.progress.pack(pady=10)
        self.progress.start()
        
        # Clear server list
        self.servers_listbox.delete(0, tk.END)
        self.discovered_servers.clear()
        
        # Start discovery thread
        self.discovery_thread = threading.Thread(target=self.discover_servers, daemon=True)
        self.discovery_thread.start()
    
    def stop_auto_discovery(self):
        """Stop auto-discovery of chat servers"""
        self.discovery_active = False
        self.progress.stop()
        self.progress.pack_forget()
    
    def discover_servers(self):
        """Listen for server broadcasts"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.broadcast_port))
            sock.settimeout(1)  # 1 second timeout for checking discovery_active flag
            
            while self.discovery_active:
                try:
                    data, addr = sock.recvfrom(1024)
                    message = data.decode('utf-8')
                    
                    # Parse server info (format: "CHAT_SERVER:IP:PORT")
                    if message.startswith("CHAT_SERVER:"):
                        parts = message.split(":")
                        if len(parts) >= 3:
                            server_ip = parts[1]
                            server_port = int(parts[2])
                            
                            # Add to discovered servers list if not already there
                            display_name = f"{server_ip}:{server_port}"
                            if display_name not in self.discovered_servers:
                                self.discovered_servers[display_name] = (server_ip, server_port)
                                self.master.after(0, lambda: self.add_server_to_list(display_name))
                except socket.timeout:
                    continue  # Just check the discovery_active flag
                except Exception as e:
                    print(f"Discovery error: {e}")
        except Exception as e:
            print(f"Discovery socket error: {e}")
        finally:
            sock.close()
    
    def add_server_to_list(self, server_name):
        """Add discovered server to the listbox"""
        # Check if already in list
        for i in range(self.servers_listbox.size()):
            if self.servers_listbox.get(i) == server_name:
                return
        
        self.servers_listbox.insert(tk.END, server_name)
        # Select first server if this is the first one
        if self.servers_listbox.size() == 1:
            self.servers_listbox.selection_set(0)
    
    def start_connection(self):
        """Start connection based on selected method"""
        # Get username first
        self.name = simpledialog.askstring("Username", "Enter your name")
        if not self.name:
            messagebox.showerror("Error", "No username provided. Using Anonymous.")
            self.name = "Anonymous"
        
        # Get server IP based on connection method
        if self.connection_var.get() == "auto":
            # Get selected server from listbox
            selection = self.servers_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a server or wait for discovery")
                return
            
            server_name = self.servers_listbox.get(selection[0])
            self.server_ip, self.server_port = self.discovered_servers[server_name]
        else:
            # Manual IP entry
            self.server_ip = self.ip_entry.get().strip()
            if not self.server_ip:
                messagebox.showerror("Error", "Please enter a server IP")
                return
        
        # Stop discovery and clear connection frame
        self.stop_auto_discovery()
        self.connect_frame.destroy()
        
        # Initialize chat UI
        self.initialize_chat_ui()
    
    def initialize_chat_ui(self):
        """Initialize the chat UI after connection details are set"""
        self.frame = tk.Frame(self.master)
        self.frame.pack(fill='both', expand=True)

        # User list with label
        self.users_frame = tk.Frame(self.frame)
        self.users_frame.pack(side='left', fill='y')
        
        self.users_label = tk.Label(self.users_frame, text="Chat Targets")
        self.users_label.pack(fill='x')
        
        self.chat_listbox = tk.Listbox(self.users_frame, width=20)
        self.chat_listbox.pack(fill='both', expand=True)
        self.chat_listbox.insert(tk.END, "Group Chat")
        self.chat_listbox.select_set(0)
        self.chat_listbox.bind('<<ListboxSelect>>', self.change_chat)

        # Current chat target
        self.current_chat = "Group Chat"

        # Dictionary to store chat histories for each conversation
        self.chat_histories = defaultdict(list)
        
        # Right panel
        self.right_panel = tk.Frame(self.frame)
        self.right_panel.pack(side='right', fill='both', expand=True)

        # Chat name label
        self.chat_name_var = tk.StringVar()
        self.chat_name_var.set("Group Chat")
        self.chat_name_label = tk.Label(self.right_panel, textvariable=self.chat_name_var, 
                                      font=("Arial", 12, "bold"), anchor=tk.W)
        self.chat_name_label.pack(fill='x')

        # Chat box
        self.chat_box = ScrolledText(self.right_panel, state="disabled")
        self.chat_box.pack(fill='both', expand=True)

        # Entry with send button in a frame
        self.input_frame = tk.Frame(self.right_panel)
        self.input_frame.pack(fill='x', pady=5)
        
        self.entry = tk.Entry(self.input_frame)
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_message)
        
        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side='right')

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Connecting to server...")
        self.status_bar = tk.Label(self.right_panel, textvariable=self.status_var, bd=1, 
                                 relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Initialize unread message counter
        self.unread_messages = defaultdict(int)
        
        # Flag to prevent double processing of sent messages
        self.message_sent = False

        # Initialize chat history with welcome messages
        self.chat_histories["Group Chat"].append("--- Welcome to Group Chat ---")
        
        # Load initial chat history
        self.load_chat_history("Group Chat")

        # Connect to server
        self.connect_to_server()
    
    # The rest of the client code remains the same as your previous implementation
    def clean_chat_name(self, chat_name):
        """Remove unread count from chat name"""
        return chat_name.split(" (")[0]
    
    def change_chat(self, event=None):
        selection = self.chat_listbox.curselection()
        if selection:
            selected_item = self.chat_listbox.get(selection[0])
            clean_name = self.clean_chat_name(selected_item)
            
            # Only update if there's a change
            if clean_name != self.current_chat:
                self.current_chat = clean_name
                self.chat_name_var.set(clean_name)
                
                # Clear unread message count for this chat
                self.unread_messages[clean_name] = 0
                self.update_chat_list_display()
                
                # Load this chat's history
                self.load_chat_history(clean_name)
    
    def load_chat_history(self, chat_name):
        """Load the chat history for the specified chat into the chat box"""
        self.chat_box.configure(state='normal')
        self.chat_box.delete(1.0, tk.END)
        
        # Initialize history for this chat if it doesn't exist
        if not self.chat_histories[chat_name]:
            self.chat_histories[chat_name].append(f"--- Beginning of conversation with {chat_name} ---")
        
        for message in self.chat_histories[chat_name]:
            self.chat_box.insert(tk.END, message + '\n')
        
        self.chat_box.see(tk.END)
        self.chat_box.configure(state='disabled')
    
    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.server_ip, self.server_port))
            self.sock.settimeout(None)

            self.sock.sendall(self.name.encode('utf-8'))

            self.status_var.set(f"Connected to {self.server_ip}:{self.server_port} as {self.name}")
            threading.Thread(target=self.receive_message, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect: {e}")
            self.status_var.set("Disconnected")
            self.master.after(2000, self.master.destroy)

    def send_message(self, event=None):
        message_text = self.entry.get().strip()
        if not message_text:
            return

        try:
            if self.current_chat == "Group Chat":
                # Mark that we're sending a message to prevent doubling
                self.message_sent = True
                
                # Send to server
                msg = f"{self.name}: {message_text}"
                self.sock.sendall(msg.encode('utf-8'))
                
                # Don't add to history here - it will come back from the server
            else:
                # Format for private message
                msg = f"@{self.current_chat}: {message_text}"
                self.sock.sendall(msg.encode('utf-8'))
                
                # For private messages, we need to manually add our outgoing message
                # to the chat history since the server confirmation comes in a different format
                display_msg = f"You: {message_text}"
                self.add_message_to_history(self.current_chat, display_msg)
            
            self.entry.delete(0, tk.END)
        except Exception as e:
            error_msg = f"[Error] Could not send message: {e}"
            self.add_message_to_history(self.current_chat, error_msg)
            self.status_var.set("Disconnected")
        
        # Reset the message sent flag after a short delay
        self.master.after(100, self.reset_message_sent_flag)
        
        return "break"  # Stops default Enter key behavior
    
    def reset_message_sent_flag(self):
        """Reset the message sent flag after a delay"""
        self.message_sent = False

    def add_message_to_history(self, chat_name, message):
        """Add a message to the specified chat history and update display if it's the current chat"""
        # Add message to chat history
        self.chat_histories[chat_name].append(message)
        
        # If this is the current chat, update the display
        if chat_name == self.current_chat:
            self.chat_box.configure(state='normal')
            self.chat_box.insert(tk.END, message + '\n')
            self.chat_box.see(tk.END)
            self.chat_box.configure(state='disabled')
        else:
            # Increment unread message counter
            self.unread_messages[chat_name] += 1
            self.update_chat_list_display()
    
    def update_chat_list_display(self):
        """Update the listbox display to show unread message counts"""
        selected_index = self.chat_listbox.curselection()
        current_selection = None
        if selected_index:
            current_selection = self.clean_chat_name(self.chat_listbox.get(selected_index[0]))
        
        # Update items with unread counts
        for i in range(self.chat_listbox.size()):
            item = self.chat_listbox.get(i)
            clean_name = self.clean_chat_name(item)
            unread = self.unread_messages[clean_name]
            
            if unread > 0:
                new_text = f"{clean_name} ({unread})"
            else:
                new_text = clean_name
                
            # Only update if needed
            if item != new_text:
                self.chat_listbox.delete(i)
                self.chat_listbox.insert(i, new_text)
        
        # Restore selection
        if current_selection:
            for i in range(self.chat_listbox.size()):
                if self.clean_chat_name(self.chat_listbox.get(i)) == current_selection:
                    self.chat_listbox.selection_clear(0, tk.END)
                    self.chat_listbox.selection_set(i)
                    break

    def receive_message(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode('utf-8')
                if not msg:
                    self.status_var.set("Server connection closed")
                    break

                # Check if it's a user list update
                if msg.startswith("/users "):
                    user_list = msg[len("/users "):].split(",")
                    self.update_user_list(user_list)
                    continue

                # Handle private messages - messages received from others
                if msg.startswith("[Private from "):
                    # Extract sender name
                    end_idx = msg.find("]")
                    if end_idx != -1:
                        sender = msg[len("[Private from "):]
                        sender = sender[:sender.find("]")]
                        
                        # Message without the prefix
                        content = msg[end_idx + 2:]  # +2 to skip "] "
                        
                        # Add message to the private chat history
                        display_msg = f"{sender}: {content}"
                        self.add_message_to_history(sender, display_msg)
                    continue
                
                # Handle private message confirmations - our messages sent to others
                if msg.startswith("[Private to "):
                    # We already added this message in the send_message method
                    # So we don't need to process it again here
                    continue

                # Handle system messages (join/leave notifications)
                if msg.startswith("*** "):
                    # Add to group chat
                    self.add_message_to_history("Group Chat", msg)
                    continue
                
                # Handle our own messages in group chat - avoid duplication
                if msg.startswith(f"{self.name}: ") and self.message_sent:
                    # Replace with "You: " format for consistency
                    display_msg = "You: " + msg[len(f"{self.name}: "):]
                    self.add_message_to_history("Group Chat", display_msg)
                    continue
                
                # Normal group message from others
                self.add_message_to_history("Group Chat", msg)

            except Exception as e:
                error_msg = f"[Error receiving] {e}"
                self.add_message_to_history(self.current_chat, error_msg)
                break
        
        self.status_var.set("Disconnected from server")

    def update_user_list(self, usernames):
        # Remember currently selected item
        selected_index = self.chat_listbox.curselection()
        current_selection = None
        if selected_index:
            current_selection = self.clean_chat_name(self.chat_listbox.get(selected_index[0]))
        
        # Store existing users for comparison
        existing_users = set()
        for i in range(1, self.chat_listbox.size()):  # Skip "Group Chat"
            existing_users.add(self.clean_chat_name(self.chat_listbox.get(i)))
        
        # Clear all except Group Chat
        self.chat_listbox.delete(1, tk.END)
        
        # Add all users except self
        for user in usernames:
            if user and user != self.name:
                # Initialize chat history if it's a new user
                if user not in existing_users and not self.chat_histories[user]:
                    self.chat_histories[user].append(f"--- Beginning of conversation with {user} ---")
                
                # Check if user has unread messages
                unread = self.unread_messages[user]
                if unread > 0:
                    self.chat_listbox.insert(tk.END, f"{user} ({unread})")
                else:
                    self.chat_listbox.insert(tk.END, user)
        
        # Try to restore selection
        if current_selection:
            for i in range(self.chat_listbox.size()):
                if self.clean_chat_name(self.chat_listbox.get(i)) == current_selection:
                    self.chat_listbox.selection_clear(0, tk.END)
                    self.chat_listbox.selection_set(i)
                    break

def main():
    root = tk.Tk()
    root.geometry("800x600")
    app = ClientClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
# ==== GUI CODE END ====
