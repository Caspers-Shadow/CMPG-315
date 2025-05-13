import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog
import socketio
import threading

# --- CLIENT SETUP ---
sio = socketio.Client()
username = ""
connected_users = []  # Track connected users

# --- GUI SETUP ---
class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        

        # Modern colors and logo
        self.accent_color = "#7ED321"
        self.bg_color = "#ffffff"
        self.text_color = "#333333"
        self.secondary_bg = "#f4f4f4"

        master.geometry("700x500")
        master.configure(bg=self.bg_color)
        master.title("Socket.IO Chat")

        # Main window styling
        master.geometry("700x500")
        master.configure(bg="#f0f0f0")
        
        # Username input frame (initial view)
        self.username_frame = tk.Frame(master, bg=self.bg_color)

        # Optional logo display
        try:
            self.logo = tk.PhotoImage(file="Chat app logo-Photoroom.png")
            self.logo_label = tk.Label(self.username_frame, image=self.logo, bg=self.bg_color)
            self.logo_label.pack(pady=(40, 10))
        except:
            pass  # Skip logo if not found
        self.username_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.username_label = tk.Label(self.username_frame, text="Enter your username:", 
                                    font=("Helvetica", 12), bg="#f0f0f0")
        self.username_label.pack(pady=(150, 10))

        self.username_entry = tk.Entry(self.username_frame, font=("Segoe UI", 13), width=30, bg=self.secondary_bg, bd=0, relief="flat", highlightthickness=1, highlightbackground=self.accent_color)
        self.username_entry.pack(pady=10)
        self.username_entry.focus()  # Set focus to the entry

        self.username_button = tk.Button(self.username_frame, text="Connect", font=("Segoe UI", 12, "bold"), bg=self.accent_color, fg="white", activebackground="#6EC51B", activeforeground="white", relief="flat", command=self.submit_username, cursor="hand2")
        self.username_button.pack(pady=10)
        
        # Chat UI elements (hidden until username is submitted)
        self.chat_frame = tk.Frame(master)
        
        # Create tabs for different chats
        self.tab_control = ttk.Notebook(self.chat_frame)
        
        # Group chat tab
        self.group_tab = tk.Frame(self.tab_control)
        self.tab_control.add(self.group_tab, text="Group Chat")
        
        # Dictionary to store private chat tabs and their content
        self.private_tabs = {}
        
        # Online users sidebar
        self.sidebar_frame = tk.Frame(self.chat_frame, bg="#e0e0e0", width=150)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        self.online_label = tk.Label(self.sidebar_frame, text="Online Users", 
                                  font=("Helvetica", 12, "bold"), bg="#e0e0e0")
        self.online_label.pack(pady=5)
        
        self.users_listbox = tk.Listbox(self.sidebar_frame, font=("Helvetica", 11), 
                                     bg="white", height=15, width=15)
        self.users_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.users_listbox.bind("<Double-1>", self.open_private_chat)
        
        # Tab content setup
        self.setup_group_tab()
        
        # Main chat area
        self.tab_control.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
    def setup_group_tab(self):
        # Message display area
        self.group_text_area = scrolledtext.ScrolledText(self.group_tab, wrap=tk.WORD, 
                                                      state='disabled', height=20, 
                                                      font=("Helvetica", 11), bg="#ffffff")
        self.group_text_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # Input frame
        input_frame = tk.Frame(self.group_tab)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.group_entry = tk.Entry(input_frame, font=("Helvetica", 11), width=50)
        self.group_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.group_entry.bind("<Return>", lambda event: self.send_group_message())
        
        self.group_send_button = tk.Button(input_frame, text="Send", font=("Helvetica", 11), 
                                        bg="#4CAF50", fg="white", 
                                        command=self.send_group_message)
        self.group_send_button.pack(side=tk.RIGHT, padx=5)

    def setup_private_tab(self, to_user):
        # Create a new frame for the private chat
        private_tab = tk.Frame(self.tab_control)
        
        # Message display area
        text_area = scrolledtext.ScrolledText(private_tab, wrap=tk.WORD, state='disabled', 
                                           height=20, font=("Helvetica", 11), bg="#ffffff")
        text_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # Input frame
        input_frame = tk.Frame(private_tab)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        entry = tk.Entry(input_frame, font=("Helvetica", 11), width=50)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<Return>", lambda event, user=to_user: self.send_private_message(user))
        
        # Store the reference to the entry widget
        self.private_tabs[to_user] = {
            "tab": private_tab,
            "text_area": text_area,
            "entry": entry
        }
        
        send_button = tk.Button(input_frame, text="Send", font=("Helvetica", 11), 
                             bg="#4CAF50", fg="white", 
                             command=lambda user=to_user: self.send_private_message(user))
        send_button.pack(side=tk.RIGHT, padx=5)
        
        # Add the tab to the notebook
        self.tab_control.add(private_tab, text=to_user)
        
        # Switch to the new tab
        self.tab_control.select(private_tab)
        
        return private_tab

    def submit_username(self):
        global username
        username = self.username_entry.get().strip()
        if username:
            self.username_frame.pack_forget()  # Hide the username input frame
            self.chat_frame.pack(fill=tk.BOTH, expand=True)  # Show the chat UI
            
            # Connect to the server
            self.connect_to_server()

    def open_private_chat(self, event):
        selected_index = self.users_listbox.curselection()
        if selected_index:
            to_user = self.users_listbox.get(selected_index[0])
            if to_user != username:  # Don't open a chat with yourself
                if to_user not in self.private_tabs:
                    self.setup_private_tab(to_user)
                else:
                    # If tab exists, just switch to it
                    self.tab_control.select(self.private_tabs[to_user]["tab"])

    def send_group_message(self):
        msg = self.group_entry.get().strip()
        if msg:
            self.group_entry.delete(0, tk.END)
            sio.emit('group_message', {'from': username, 'message': msg})

    def send_private_message(self, to_user):
        if to_user in self.private_tabs:
            entry = self.private_tabs[to_user]["entry"]
            msg = entry.get().strip()
            if msg:
                entry.delete(0, tk.END)
                sio.emit('private_message', {'from': username, 'to': to_user, 'message': msg})
                
                # Display the message in the sender's window too
                self.display_private_message(to_user, f"[You to {to_user}] {msg}")

    def display_group_message(self, msg):
        self.group_text_area.configure(state='normal')
        self.group_text_area.insert(tk.END, f"{msg}\n")
        self.group_text_area.configure(state='disabled')
        self.group_text_area.see(tk.END)  # Auto-scroll to the bottom

    def display_private_message(self, user, msg):
        # Make sure the private tab exists
        if user not in self.private_tabs:
            self.setup_private_tab(user)
            
        text_area = self.private_tabs[user]["text_area"]
        text_area.configure(state='normal')
        text_area.insert(tk.END, f"{msg}\n")
        text_area.configure(state='disabled')
        text_area.see(tk.END)  # Auto-scroll to the bottom
        
        # If this tab is not currently selected, highlight it somehow
        current_tab = self.tab_control.select()
        if self.tab_control.index(current_tab) != self.tab_control.index(self.private_tabs[user]["tab"]):
            # You could change the tab text or color here
            tab_id = self.tab_control.index(self.private_tabs[user]["tab"])
            current_text = self.tab_control.tab(tab_id, "text")
            if not current_text.startswith("* "):
                self.tab_control.tab(tab_id, text=f"* {user}")

    def update_user_list(self, users):
        self.users_listbox.delete(0, tk.END)
        for user in users:
            if user != username:  # Don't show yourself in the list
                self.users_listbox.insert(tk.END, user)

    def connect_to_server(self):
        try:
            sio.connect("https://new-chat-app-2wtj.onrender.com")  # Change to your deployed server URL
            sio.emit('register', username)  # Register after connecting
        except Exception as e:
            self.display_group_message(f"[Error] Could not connect: {e}")

    def on_close(self):
        try:
            sio.disconnect()
        except:
            pass
        self.master.destroy()


# --- SOCKET.IO EVENTS ---
@sio.event
def connect():
    gui.display_group_message("[System] Connected to server.")

@sio.event
def disconnect():
    gui.display_group_message("[System] Disconnected from server.")

@sio.on('message')
def on_message(data):
    gui.display_group_message(f"{data}")

@sio.on('group_message')
def on_group_message(data):
    from_user = data.get('from', 'Unknown')
    message = data.get('message', '')
    gui.display_group_message(f"[{from_user}] {message}")

@sio.on('private_message')
def on_private_message(data):
    from_user = data.get('from', 'Unknown')
    message = data.get('message', '')
    
    # Display in the private chat tab
    gui.display_private_message(from_user, f"[{from_user}] {message}")

@sio.on('user_list')
def on_user_list(data):
    global connected_users
    connected_users = data
    gui.update_user_list(data)

@sio.on('user_joined')
def on_user_joined(data):
    gui.display_group_message(f"[System] {data} has joined the chat.")
    # Request updated user list
    sio.emit('get_users')

@sio.on('user_left')
def on_user_left(data):
    gui.display_group_message(f"[System] {data} has left the chat.")
    # Request updated user list
    sio.emit('get_users')

def start_gui():
    global gui
    root = tk.Tk()
    gui = ChatClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_close)
    root.mainloop()

if __name__ == "__main__":
    start_gui()