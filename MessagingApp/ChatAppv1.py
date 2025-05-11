import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox, ttk
import threading
import socket
from collections import defaultdict
import time
# import struct # struct module was imported but not used

HOST = '0.0.0.0'  # Listen on all available interfaces for the server
PORT = 12345
BROADCAST_PORT = 12346
SERVER_BROADCAST_MESSAGE = "CHAT_SERVER"
clients = {}  # username: connection (Global for server-side functions)

def get_local_ip():
    """
    Attempts to get the local IP address that can be used to connect to the server from other machines.
    Falls back to 127.0.0.1 if an external-facing IP can't be determined easily.
    """
    try:
        # Connect to an external host to find the preferred outgoing IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1) # Short timeout to avoid long hangs if no internet
        s.connect(("8.8.8.8", 80)) # Google's public DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            # Fallback: get hostname, then get IP from hostname
            # This might return 127.0.0.1 or a LAN IP
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except socket.gaierror: # gai: getaddrinfo error
            return "127.0.0.1" # Final fallback

def broadcast_server_ip():
    """Broadcast server IP periodically for auto-discovery by clients."""
    server_lan_ip = get_local_ip()
    print(f"[BROADCASTING] Server IP: {server_lan_ip} on broadcast port {BROADCAST_PORT} for TCP port {PORT}")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(('', 0))  # Bind to any available port for sending

    message = f"{SERVER_BROADCAST_MESSAGE}:{server_lan_ip}:{PORT}".encode('utf-8')

    try:
        while True: # This loop will be controlled by the daemon status of the thread
            s.sendto(message, ('<broadcast>', BROADCAST_PORT))
            time.sleep(2)  # Broadcast every 2 seconds
    except Exception as e:
        print(f"[ERROR] Broadcasting stopped: {e}")
    finally:
        s.close()

def handle_client(conn, addr, _gui_instance_placeholder): # gui_instance not used by server
    print(f"[NEW CLIENT CONNECTED] {addr} to local server.")
    username = None
    try:
        username = conn.recv(1024).decode('utf-8').strip()
        if not username: # Handle empty username
            print(f"[CONNECTION REJECTED] Empty username from {addr}.")
            conn.sendall("Username cannot be empty.".encode('utf-8'))
            conn.close()
            return

        if username in clients:
            print(f"[CONNECTION REJECTED] Username {username} already taken by {addr}.")
            conn.sendall(f"Username '{username}' already taken.".encode('utf-8'))
            conn.close()
            return

        clients[username] = conn
        print(f"[REGISTERED] '{username}' from {addr}")

        send_user_list(conn) # Send current user list to the new client

        announcement = f"*** {username} has joined the chat ***"
        broadcast(announcement, exclude=conn) # Announce new user to others
        update_all_users() # Update user list for all clients

        while True:
            msg_bytes = conn.recv(1024) # Receive raw bytes
            if not msg_bytes: # Connection closed by client
                break
            msg = msg_bytes.decode('utf-8') # Decode after checking for empty

            print(f"[{username}] says: {msg}")

            if msg.startswith("@"): # Private message
                try:
                    parts = msg.split(":", 1)
                    if len(parts) != 2:
                        conn.sendall("Invalid private message format. Use @username: message".encode('utf-8'))
                        continue
                    target_user = parts[0][1:].strip()
                    content = parts[1].strip()

                    if target_user in clients:
                        private_msg_to_target = f"[Private from {username}] {content}"
                        clients[target_user].sendall(private_msg_to_target.encode('utf-8'))
                        
                        confirmation_to_sender = f"[Private to {target_user}] {content}"
                        conn.sendall(confirmation_to_sender.encode('utf-8'))
                    else:
                        conn.sendall(f"User '{target_user}' not found or not online.".encode('utf-8'))
                except Exception as e:
                    print(f"Private message processing error for {username}: {e}")
                    conn.sendall("Error processing your private message.".encode('utf-8'))
            else: # Group message (client sends "SenderName: MessageText")
                  # Server broadcasts it as is.
                broadcast(msg) # Server broadcasts the client-formatted message
    except ConnectionResetError:
        print(f"[CONNECTION RESET] by {username if username else addr}.")
    except Exception as e:
        print(f"[ERROR] In handle_client for {username if username else addr}: {e}")
    finally:
        if username and username in clients:
            del clients[username]
            leave_msg = f"*** {username} has left the chat ***"
            broadcast(leave_msg)
            update_all_users() # Update user lists after someone leaves
        if conn:
            conn.close()
        print(f"[DISCONNECTED] {username if username else addr}.")


def send_user_list(conn):
    """Send list of active users to a specific client connection."""
    users = ",".join(clients.keys())
    msg = f"/users {users}"
    try:
        conn.sendall(msg.encode('utf-8'))
    except Exception as e:
        print(f"Error sending user list to a client: {e}")

def update_all_users():
    """Send updated user list to all currently connected clients."""
    for conn_in_dict in clients.values():
        send_user_list(conn_in_dict)

def broadcast(message, exclude=None):
    """Send message to all clients except the excluded one (if any)."""
    for user_conn in list(clients.values()): # Iterate over a copy in case clients dict changes
        if user_conn != exclude:
            try:
                user_conn.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Broadcast error to a client: {e}. Removing problematic client.")
                # Basic error handling: find and remove client causing issues
                for uname, c in list(clients.items()):
                    if c == user_conn:
                        del clients[uname]
                        update_all_users() # Update user list for remaining clients
                        break


class ClientClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("P2P Chat Client")

        self.server_ip = None
        self.server_port = None
        self.broadcast_port = BROADCAST_PORT # Use global
        self.sock = None # For client connection to a server
        self.name = None
        self.connected = False # True if client is connected to a chat server
        self.discovered_servers = {} # {ip_str: port_int}

        self.server_thread = None # For the local server instance
        self.local_server_status_var = tk.StringVar()
        self.local_server_active = False # True if local server is successfully running

        self.setup_connection_ui()
        self.start_local_server() # Attempt to start the local server
        
        # Start listening for other servers
        threading.Thread(target=self.listen_for_servers, daemon=True).start()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)


    def setup_connection_ui(self):
        # Destroy chat UI elements if they exist
        if hasattr(self, 'frame') and self.frame.winfo_exists():
            self.frame.destroy()
        if hasattr(self, 'status_bar_chat') and self.status_bar_chat.winfo_exists():
            self.status_bar_chat.destroy()
            delattr(self, 'status_bar_chat') # Remove attribute to prevent errors on re-creation

        # Create or re-pack connection frame
        if hasattr(self, 'connection_frame') and self.connection_frame.winfo_exists():
            self.connection_frame.destroy() # Ensure clean slate for connection UI
        
        self.connection_frame = tk.Frame(self.master)
        self.connection_frame.pack(pady=10, fill='both', expand=True)

        # Local Server Status Label
        if not hasattr(self, 'local_server_status_var'): # Should be set in __init__
            self.local_server_status_var = tk.StringVar()
            self.local_server_status_var.set("Local server: Status unknown")
        self.local_server_status_label = tk.Label(self.connection_frame, textvariable=self.local_server_status_var, font=("Arial", 9, "italic"))
        self.local_server_status_label.pack(pady=(5,10))

        self.auto_connect_label = tk.Label(self.connection_frame, text="Discovered Servers:")
        self.auto_connect_label.pack()

        self.server_list = tk.Listbox(self.connection_frame, width=40, height=5)
        self.server_list.pack(pady=5)
        self.server_list.bind('<<ListboxSelect>>', self.enable_connect_button)

        self.connect_button = tk.Button(self.connection_frame, text="Connect to Selected", state=tk.DISABLED, command=self.connect_to_discovered)
        self.connect_button.pack(pady=5)

        self.manual_label = tk.Label(self.connection_frame, text="Manually Connect:")
        self.manual_label.pack(pady=(10,0))

        ip_frame = tk.Frame(self.connection_frame)
        ip_frame.pack()
        tk.Label(ip_frame, text="IP:").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(ip_frame, width=20)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(ip_frame, text="Port:").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(ip_frame, width=7)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.pack(side=tk.LEFT)
        
        self.manual_connect_button = tk.Button(self.connection_frame, text="Connect Manually", command=self.connect_manually)
        self.manual_connect_button.pack(pady=10)

        # Connection UI specific status bar
        if not hasattr(self, 'status_var_connection'):
            self.status_var_connection = tk.StringVar()
        self.status_var_connection.set("Searching for servers... Your local server status is above.")
        if hasattr(self, 'status_bar_connection') and self.status_bar_connection.winfo_exists():
             self.status_bar_connection.destroy()
        self.status_bar_connection = tk.Label(self.master, textvariable=self.status_var_connection, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar_connection.pack(side=tk.BOTTOM, fill=tk.X)

    def enable_connect_button(self, _event=None):
        if self.server_list.curselection():
            self.connect_button.config(state=tk.NORMAL)
        else:
            self.connect_button.config(state=tk.DISABLED)

    def listen_for_servers(self):
        listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            listener_socket.bind(('', self.broadcast_port)) # Listen on broadcast port
            listener_socket.settimeout(3) # Timeout for recvfrom
            print(f"[DISCOVERY LISTENER] Listening for server broadcasts on port {self.broadcast_port}")
        except Exception as e:
            print(f"[DISCOVERY LISTENER] Error binding: {e}. Auto-discovery may not work.")
            if hasattr(self, 'status_var_connection'):
                self.master.after(0, lambda: self.status_var_connection.set("Error starting discovery listener."))
            return

        while True:
            if self.connected: # If client is connected to a server, stop listening for others
                time.sleep(1) # Keep thread alive but idle
                continue
            try:
                data, _addr = listener_socket.recvfrom(1024) # Sender address not crucial here
                message = data.decode('utf-8')
                if message.startswith(f"{SERVER_BROADCAST_MESSAGE}:"):
                    parts = message.split(":")
                    if len(parts) == 3:
                        s_ip, s_port_str = parts[1], parts[2]
                        s_port = int(s_port_str)
                        server_key = f"{s_ip}:{s_port}"
                        
                        # Avoid adding its own server if it's the one this client instance is hosting
                        my_local_ip = get_local_ip()
                        if s_ip == my_local_ip and s_port == PORT and self.local_server_active:
                            # print(f"[DISCOVERY] Ignored own local server broadcast from {s_ip}:{s_port}")
                            continue

                        if server_key not in self.discovered_servers:
                            self.discovered_servers[server_key] = (s_ip, s_port)
                            self.server_list.insert(tk.END, server_key)
                            print(f"[DISCOVERED] Server at {server_key}")
                            if hasattr(self, 'status_var_connection'):
                                 self.master.after(0, lambda sk=server_key: self.status_var_connection.set(f"Found: {sk}"))
            except socket.timeout:
                if not self.discovered_servers and hasattr(self, 'status_var_connection'):
                    self.master.after(0, lambda: self.status_var_connection.set("Searching for servers..."))
            except Exception as e:
                print(f"[DISCOVERY LISTENER] Error: {e}")
                time.sleep(2) # Wait a bit before retrying after an error
            # Check self.master.winfo_exists() to allow thread to terminate if GUI closed
            if not self.master.winfo_exists():
                break
        listener_socket.close()
        print("[DISCOVERY LISTENER] Stopped.")


    def _run_server(self):
        current_ip = get_local_ip()
        server_socket_instance = None # Explicitly define for finally block
        try:
            # Update GUI from main thread using master.after
            self.master.after(0, lambda: self.local_server_status_var.set(f"Local server: Starting on {current_ip}:{PORT}..."))
            
            server_socket_instance = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket_instance.bind((HOST, PORT)) # HOST is '0.0.0.0'
            server_socket_instance.listen()
            
            self.local_server_active = True # Set flag indicating server is running
            self.master.after(0, lambda: self.local_server_status_var.set(f"Local server: Listening on {current_ip}:{PORT}"))
            print(f"[LOCAL SERVER] Listening on {current_ip}:{PORT}")

            # Start broadcasting server IP for auto-discovery ONLY if server started successfully
            broadcast_thread = threading.Thread(target=broadcast_server_ip, daemon=True)
            broadcast_thread.start()

            while self.local_server_active:
                try:
                    conn, addr = server_socket_instance.accept()
                    if not self.local_server_active: # Re-check after blocking accept
                        conn.close()
                        break
                    # Pass None for gui_instance as server functions don't need it
                    client_handler_thread = threading.Thread(target=handle_client, args=(conn, addr, None), daemon=True)
                    client_handler_thread.start()
                except socket.error as e: # Handle socket-specific errors during accept
                    if self.local_server_active: # Only log if we weren't trying to shut down
                        print(f"[LOCAL SERVER] Socket error accepting connection: {e}")
                    break # Exit the accept loop
                except Exception as e:
                    if self.local_server_active:
                        print(f"[LOCAL SERVER] Error accepting connection: {e}")
                    break
        except OSError as e:
            self.local_server_active = False
            if e.errno == 98: # Address already in use (EADDRINUSE)
                err_msg = f"Local server: FAILED (Port {PORT} is already in use)"
                print(f"[ERROR] {err_msg}")
                self.master.after(0, lambda: self.local_server_status_var.set(err_msg))
            else:
                err_msg = f"Local server: FAILED (OS Error: {e})"
                print(f"[ERROR] {err_msg}")
                self.master.after(0, lambda: self.local_server_status_var.set(err_msg))
        except Exception as e:
            self.local_server_active = False
            err_msg = f"Local server: FAILED to start ({e})"
            print(f"[ERROR] {err_msg}")
            self.master.after(0, lambda: self.local_server_status_var.set(err_msg))
        finally:
            if server_socket_instance:
                server_socket_instance.close()
            self.local_server_active = False # Ensure flag is false when server stops
            # Update status if it hasn't been set by a specific error message
            final_status = self.local_server_status_var.get()
            if "Listening" in final_status or "Starting" in final_status : # If it was running or starting
                self.master.after(0, lambda: self.local_server_status_var.set("Local server: Stopped."))
            print("[LOCAL SERVER THREAD] Terminated.")

    def start_local_server(self):
        if not hasattr(self, 'server_thread') or not self.server_thread.is_alive():
            self.local_server_active = True # Assume it will start; _run_server will correct if fails
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            print("[INFO] Local server thread initiated.")
        else:
            print("[INFO] Local server thread already running or was initiated.")
            # Refresh status based on current flag
            if self.local_server_active:
                 self.master.after(0, lambda: self.local_server_status_var.set(f"Local server: Believed to be running on {get_local_ip()}:{PORT}"))
            else:
                 # This case might occur if thread exists but _run_server failed before setting active
                 self.master.after(0, lambda: self.local_server_status_var.set(f"Local server: Status uncertain (thread exists)."))


    def stop_local_server(self):
        """Signals the local server thread to stop accepting new connections and terminate."""
        self.local_server_active = False # Signal server loop in _run_server to stop
        print("[INFO] Signalling local server thread to stop.")
        # To ensure accept() unblocks, one might make a dummy connection to localhost:PORT
        # This is a simpler approach for now. The socket closing in finally should help.
        try:
            # Create a dummy connection to unblock server_socket_instance.accept()
            # This helps the server thread to exit its loop cleanly if it's stuck on accept()
            dummy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dummy_socket.settimeout(0.5) # Don't block indefinitely for this dummy connection
            dummy_socket.connect((get_local_ip(), PORT)) # Connect to own server
            dummy_socket.close()
        except Exception:
            # This might fail if the server wasn't listening or already closed, which is fine.
            # print(f"[INFO] Dummy connection for server shutdown: {e}")
            pass


    def on_closing(self):
        """Handles GUI window closing."""
        print("[INFO] Application closing procedure initiated...")
        self.connected = False # This should signal listen_for_servers to wind down if it checks

        self.stop_local_server() # Signal local server to stop

        if self.sock: # If client is connected to a server
            try:
                print("[INFO] Closing client connection socket.")
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception as e:
                print(f"[ERROR] While closing client socket: {e}")
        
        # Wait briefly for threads to attempt to close, if joinable
        if hasattr(self, 'server_thread') and self.server_thread.is_alive():
            print("[INFO] Waiting for local server thread to join...")
            self.server_thread.join(timeout=0.5) # Wait max 0.5 sec
            if self.server_thread.is_alive():
                print("[WARNING] Local server thread did not join in time.")
        
        # Other listener threads are daemons, will exit with main.
        print("[INFO] Destroying main window.")
        self.master.destroy()

    def connect_to_discovered(self):
        selected_indices = self.server_list.curselection()
        if selected_indices:
            server_key = self.server_list.get(selected_indices[0])
            if server_key in self.discovered_servers:
                self.server_ip, self.server_port = self.discovered_servers[server_key]
                self.start_chat_ui()
            else: # Should not happen if listbox is in sync with discovered_servers
                messagebox.showerror("Error", "Selected server not found in discovery data.")


    def connect_manually(self):
        ip = self.ip_entry.get().strip()
        port_str = self.port_entry.get().strip()
        if not ip:
            messagebox.showerror("Error", "IP address cannot be empty.")
            return
        if not port_str.isdigit():
            messagebox.showerror("Error", "Port must be a number.")
            return
        
        self.server_ip, self.server_port = ip, int(port_str)
        self.start_chat_ui()

    def start_chat_ui(self):
        if not self.server_ip or not self.server_port:
            messagebox.showerror("Connection Error", "Server IP or Port not set.")
            return

        self.connected = True # Signal to stop server discovery listener loop
        if hasattr(self, 'connection_frame') and self.connection_frame.winfo_exists():
            self.connection_frame.destroy()
        if hasattr(self, 'status_bar_connection') and self.status_bar_connection.winfo_exists():
            self.status_bar_connection.destroy()
            delattr(self, 'status_bar_connection')

        self.name = simpledialog.askstring("Username", "Enter your name:", parent=self.master)
        if not self.name: # User pressed cancel or entered empty
            self.name = f"User{int(time.time() % 1000)}" # Default unique-ish name
            messagebox.showinfo("Info", f"No username provided. Using '{self.name}'.", parent=self.master)
        
        self.initialize_chat_ui()
        self.connect_to_server()


    def initialize_chat_ui(self):
        """Initializes the main chat interface widgets."""
        self.frame = tk.Frame(self.master)
        self.frame.pack(fill='both', expand=True)

        # Left panel for user list
        self.users_frame = tk.Frame(self.frame, width=150) # Give it a default width
        self.users_frame.pack(side='left', fill='y', padx=5, pady=5)
        self.users_frame.pack_propagate(False) # Prevent resizing based on content

        self.users_label = tk.Label(self.users_frame, text="Chat Targets")
        self.users_label.pack(fill='x')

        self.chat_listbox = tk.Listbox(self.users_frame) # Width managed by frame
        self.chat_listbox.pack(fill='both', expand=True)
        self.chat_listbox.insert(tk.END, "Group Chat")
        self.chat_listbox.select_set(0) # Select "Group Chat" by default
        self.chat_listbox.bind('<<ListboxSelect>>', self.change_chat)

        self.current_chat = "Group Chat" # Default active chat
        self.chat_histories = defaultdict(list) # Stores message history for each chat

        # Right panel for chat messages and input
        self.right_panel = tk.Frame(self.frame)
        self.right_panel.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        self.chat_name_var = tk.StringVar()
        self.chat_name_var.set("Group Chat") # Display current chat name
        self.chat_name_label = tk.Label(self.right_panel, textvariable=self.chat_name_var,
                                        font=("Arial", 12, "bold"), anchor=tk.W)
        self.chat_name_label.pack(fill='x')

        self.chat_box = ScrolledText(self.right_panel, state="disabled", wrap=tk.WORD)
        self.chat_box.pack(fill='both', expand=True, pady=5)

        # Input area
        self.input_frame = tk.Frame(self.right_panel)
        self.input_frame.pack(fill='x')

        self.entry = tk.Entry(self.input_frame)
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side='right')

        # Chat UI specific status bar
        if not hasattr(self, 'status_var_chat'):
            self.status_var_chat = tk.StringVar()
        self.status_var_chat.set(f"Attempting to connect to {self.server_ip}:{self.server_port}...")
        if hasattr(self, 'status_bar_chat') and self.status_bar_chat.winfo_exists():
            self.status_bar_chat.destroy() # Should have been deleted by setup_connection_ui
        self.status_bar_chat = tk.Label(self.master, textvariable=self.status_var_chat, bd=1,
                                      relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar_chat.pack(side=tk.BOTTOM, fill=tk.X)


        self.unread_messages = defaultdict(int) # Counts unread messages for each chat target
        self.message_sent = False # Flag for identifying sender's own group messages

        # Initialize and load history for the default group chat
        self.chat_histories["Group Chat"].append("--- Welcome to Group Chat ---")
        self.load_chat_history("Group Chat")


    def connect_to_server(self):
        """Establishes connection to the selected chat server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10) # Connection timeout
            self.sock.connect((self.server_ip, self.server_port))
            self.sock.settimeout(None) # Back to blocking mode for recv

            self.sock.sendall(self.name.encode('utf-8')) # Send username
            
            # Check server response for username validity
            response = self.sock.recv(1024).decode('utf-8')
            if response.startswith("Username") and "already taken" in response:
                messagebox.showerror("Username Error", response, parent=self.master)
                self.sock.close()
                self.connected = False # Reset flag
                self.master.after(0, self.setup_connection_ui) # Go back to connection screen
                return
            elif response.startswith("Username cannot be empty"): # Should be caught client-side mostly
                messagebox.showerror("Username Error", response, parent=self.master)
                self.sock.close()
                self.connected = False
                self.master.after(0, self.setup_connection_ui)
                return
            else:
                # If server sends an unexpected initial message that's not an error,
                # it might be the user list or a welcome. For now, assume successful connection.
                # A more robust handshake might be needed if server sends varied initial messages.
                # The current server sends user list *after* registration.
                # Let's assume an empty response or a non-error implies success for now.
                 if hasattr(self, 'status_var_chat'):
                    self.status_var_chat.set(f"Connected to {self.server_ip}:{self.server_port} as {self.name}")
                print(f"[CLIENT] Connected to {self.server_ip}:{self.server_port} as {self.name}")
                
                # Start receiving messages in a new thread
                threading.Thread(target=self.receive_message, daemon=True).start()
                
                # Manually process the first potential message if it was part of "response"
                if response and not (response.startswith("Username") and "taken" in response):
                    self.process_incoming_message(response)


        except socket.timeout:
            messagebox.showerror("Connection Error", f"Connection to {self.server_ip}:{self.server_port} timed out.", parent=self.master)
            self.handle_connection_failure()
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", f"Connection to {self.server_ip}:{self.server_port} was refused.", parent=self.master)
            self.handle_connection_failure()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to {self.server_ip}:{self.server_port}: {e}", parent=self.master)
            self.handle_connection_failure()

    def handle_connection_failure(self):
        """Helper to reset state and UI on connection failure."""
        self.connected = False
        if hasattr(self, 'status_var_chat'):
            self.status_var_chat.set("Disconnected. Connection failed.")
        elif hasattr(self, 'status_var_connection'):
             self.status_var_connection.set("Connection failed. Try again.")
        
        # Ensure socket is closed
        if self.sock:
            try: self.sock.close()
            except: pass
            self.sock = None

        # Go back to connection UI
        # This needs to ensure chat UI is cleaned up by setup_connection_ui
        self.master.after(0, self.setup_connection_ui)


    def clean_chat_name(self, chat_name_with_count):
        """Removes unread count like '(2)' from a chat name string."""
        return chat_name_with_count.split(" (")[0]

    def change_chat(self, _event=None):
        """Handles selection change in the chat_listbox."""
        selection = self.chat_listbox.curselection()
        if selection:
            selected_item_text = self.chat_listbox.get(selection[0])
            cleaned_name = self.clean_chat_name(selected_item_text)

            if cleaned_name != self.current_chat:
                self.current_chat = cleaned_name
                self.chat_name_var.set(cleaned_name) # Update label for current chat name
                self.unread_messages[cleaned_name] = 0 # Clear unread count for this chat
                self.update_chat_list_display() # Refresh listbox display (remove count)
                self.load_chat_history(cleaned_name) # Load history for the new current chat


    def load_chat_history(self, chat_name_key):
        """Loads and displays message history for the specified chat_name_key."""
        self.chat_box.configure(state='normal')
        self.chat_box.delete(1.0, tk.END)
        if not self.chat_histories[chat_name_key]: # Initialize if empty
            self.chat_histories[chat_name_key].append(f"--- Beginning of conversation with {chat_name_key} ---")
        for message in self.chat_histories[chat_name_key]:
            self.chat_box.insert(tk.END, message + '\n')
        self.chat_box.see(tk.END) # Scroll to the end
        self.chat_box.configure(state='disabled')


    def send_message(self, _event=None): # event is passed by <Return> binding
        """Sends a message to the current chat target (group or private)."""
        message_text = self.entry.get().strip()
        if not message_text or not self.connected or not self.sock:
            return "break" # Consume the event, do nothing

        try:
            formatted_message_to_send = ""
            if self.current_chat == "Group Chat":
                self.message_sent = True # Flag to identify own message from server echo
                formatted_message_to_send = f"{self.name}: {message_text}" # Client formats group messages
                self.sock.sendall(formatted_message_to_send.encode('utf-8'))
                # Own group message will be added to history when received from server
            else: # Private message
                formatted_message_to_send = f"@{self.current_chat}: {message_text}"
                self.sock.sendall(formatted_message_to_send.encode('utf-8'))
                # Display own private message immediately
                display_msg_for_self = f"You: {message_text}"
                self.add_message_to_history(self.current_chat, display_msg_for_self)
            
            self.entry.delete(0, tk.END) # Clear input field
        except Exception as e:
            error_msg = f"[Error sending message]: {e}"
            self.add_message_to_history(self.current_chat, error_msg)
            if hasattr(self, 'status_var_chat'):
                self.status_var_chat.set("Disconnected (send error).")
            self.connected = False # Assume disconnection
            # Potentially trigger reconnection UI or alert user more strongly.
        finally:
            # Reset message_sent flag after a short delay (for group messages)
            if self.current_chat == "Group Chat":
                 self.master.after(200, self.reset_message_sent_flag) # Increased delay slightly

        return "break" # Stops default Enter key behavior in Entry


    def reset_message_sent_flag(self):
        """Resets the message_sent flag."""
        self.message_sent = False

    def add_message_to_history(self, chat_name_key, message_content):
        """Adds a message to the history of chat_name_key and updates UI if current."""
        self.chat_histories[chat_name_key].append(message_content)
        if chat_name_key == self.current_chat:
            self.chat_box.configure(state='normal')
            self.chat_box.insert(tk.END, message_content + '\n')
            self.chat_box.see(tk.END)
            self.chat_box.configure(state='disabled')
        else: # Increment unread count for non-active chats
            self.unread_messages[chat_name_key] += 1
            self.update_chat_list_display()


    def update_chat_list_display(self):
        """Updates the chat_listbox items to show unread message counts."""
        selected_idx_before_update = self.chat_listbox.curselection()
        
        for i in range(self.chat_listbox.size()):
            item_text = self.chat_listbox.get(i)
            clean_name = self.clean_chat_name(item_text)
            unread_count = self.unread_messages[clean_name]
            
            new_display_text = f"{clean_name} ({unread_count})" if unread_count > 0 else clean_name
            
            if item_text != new_display_text:
                self.chat_listbox.delete(i)
                self.chat_listbox.insert(i, new_display_text)
        
        # Restore selection if it existed
        if selected_idx_before_update:
            self.chat_listbox.selection_set(selected_idx_before_update[0])


    def process_incoming_message(self, msg):
        """Processes a single incoming message string."""
        if not msg: return

        if msg.startswith("/users "):
            user_list_str = msg[len("/users "):]
            # Filter out empty strings that might result from splitting an empty list
            active_usernames = [name for name in user_list_str.split(",") if name]
            self.update_user_list(active_usernames)
            return # Handled

        if msg.startswith("[Private from "):
            end_idx = msg.find("]")
            if end_idx != -1:
                # Corrected sender extraction for robustness
                sender_part = msg[len("[Private from "):end_idx]
                actual_sender_name = sender_part.strip()
                
                message_content = msg[end_idx + 2:].strip() # +2 for "] "
                
                # If this is a PM from self (echoed back, though server doesn't do this for PMs usually)
                # The fix for self-PMs is that 'send_message' adds "You: ...",
                # and server confirmation "[Private to ...]" is ignored.
                # This path is for PMs *received from others*.
                if actual_sender_name != self.name:
                    display_msg = f"{actual_sender_name}: {message_content}"
                    self.add_message_to_history(actual_sender_name, display_msg)
                # If actual_sender_name == self.name, it implies a message I sent to myself
                # that the server routed back as if from another. This is handled by the
                # client displaying "You: ..." on send and server sending confirmation.
                # The current server sends "[Private to target]" to sender, which is ignored.
                # So, this `actual_sender_name != self.name` check is mostly for clarity,
                # as PMs from self shouldn't arrive in this "[Private from self]" format from this server.
            return # Handled

        if msg.startswith("[Private to "):
            # This is a confirmation from the server that our private message was sent.
            # We already added "You: ..." to our local chat history when we sent it.
            # So, we just ignore this confirmation to avoid duplication.
            return # Handled

        if msg.startswith("*** "): # System messages (join/leave notifications)
            self.add_message_to_history("Group Chat", msg)
            return # Handled

        # Handle our own group messages echoed back by the server
        # Server broadcasts "SenderName: MessageText"
        if msg.startswith(f"{self.name}: ") and self.message_sent:
            actual_message_content = msg[len(f"{self.name}: "):].strip()
            display_msg_for_self = f"You: {actual_message_content}"
            self.add_message_to_history("Group Chat", display_msg_for_self)
            # self.message_sent flag will be reset by timer
            return # Handled
        
        # If it's a group message from another user, or potentially our own if message_sent flag was missed (unlikely with timer)
        # Assumed to be "SenderName: MessageText"
        self.add_message_to_history("Group Chat", msg)


    def receive_message(self):
        """Continuously receives messages from the server in a dedicated thread."""
        buffer = ""
        while self.connected and self.sock:
            try:
                data_chunk = self.sock.recv(1024).decode('utf-8')
                if not data_chunk: # Server closed connection
                    if hasattr(self, 'status_var_chat'):
                        self.status_var_chat.set("Connection closed by server.")
                    break 
                
                buffer += data_chunk
                # Process messages separated by newlines if server sends them that way
                # For this app, server sends one message at a time, not newline-separated stream.
                # So, we process the buffer as one message. If server logic changes, this might need adjustment.
                # For now, assuming each recv() is a complete message or part of one.
                # The current server sends distinct messages, so buffer might not be strictly necessary
                # unless messages can be fragmented over TCP, which recv(1024) tries to get.

                # Let's assume each recv might be a full message from this server's design
                self.process_incoming_message(buffer.strip()) # Process the received data
                buffer = "" # Clear buffer after processing


            except ConnectionResetError:
                if hasattr(self, 'status_var_chat'):
                    self.status_var_chat.set("Connection reset by server.")
                break 
            except socket.error as e: # Catch other socket errors (e.g. if socket closed abruptly)
                 if self.connected: # Only if we thought we were connected
                    if hasattr(self, 'status_var_chat'):
                        self.status_var_chat.set(f"Socket error: {e}")
                 break
            except Exception as e:
                if self.connected: # Only log if we thought we were connected
                    print(f"[ERROR] In receive_message: {e}")
                    # self.add_message_to_history(self.current_chat, f"[Error receiving]: {e}")
                break # Exit loop on other critical errors
        
        # Loop exited, means disconnection
        self.connected = False
        if self.master.winfo_exists(): # Check if GUI is still there
            if hasattr(self, 'status_var_chat') and "Connected" in self.status_var_chat.get() :
                 self.status_var_chat.set("Disconnected.")
            # If GUI exists, go back to connection screen
            self.master.after(0, self.setup_connection_ui)
        print("[RECEIVE THREAD] Terminated.")


    def update_user_list(self, active_usernames):
        """Updates the chat_listbox with the current list of users."""
        selected_item_text = None
        if self.chat_listbox.curselection():
            selected_item_text = self.chat_listbox.get(self.chat_listbox.curselection()[0])
        
        # Preserve "Group Chat" and clear other users
        self.chat_listbox.delete(1, tk.END) 
        
        # Get current users in listbox (should only be "Group Chat" now)
        current_listbox_users = {self.clean_chat_name(self.chat_listbox.get(i)) for i in range(self.chat_listbox.size())}

        for uname in sorted(active_usernames): # Sort for consistent order
            if uname == self.name: # Don't list self as a chat target
                continue
            if uname not in current_listbox_users:
                # Initialize history if this user is new to us
                if not self.chat_histories[uname]:
                    self.chat_histories[uname].append(f"--- Beginning of conversation with {uname} ---")
                
                unread_count = self.unread_messages[uname]
                display_text = f"{uname} ({unread_count})" if unread_count > 0 else uname
                self.chat_listbox.insert(tk.END, display_text)
        
        # Try to restore selection
        if selected_item_text:
            cleaned_selection = self.clean_chat_name(selected_item_text)
            for i in range(self.chat_listbox.size()):
                if self.clean_chat_name(self.chat_listbox.get(i)) == cleaned_selection:
                    self.chat_listbox.selection_clear(0, tk.END)
                    self.chat_listbox.selection_set(i)
                    self.chat_listbox.activate(i)
                    break
        elif self.chat_listbox.size() > 0 and not self.chat_listbox.curselection(): # Default if nothing selected
            self.chat_listbox.select_set(0) # Select "Group Chat"
            self.change_chat() # Trigger UI update for this selection


def main():
    root = tk.Tk()
    root.geometry("700x500") # Adjusted size slightly
    app = ClientClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()