import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox
import threading
import socket
from collections import defaultdict

class ClientClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Chat Client")
        
        self.server_ip = "192.168.0.26"  # replace with server IP if needed

        self.name = simpledialog.askstring("Username", "Enter your name")
        if not self.name:
            messagebox.showerror("Error", "No username provided. Using Anonymous.")
            self.name = "Anonymous"
        
        self.frame = tk.Frame(master)
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

        self.connect_to_server()
    
    def change_chat(self, event=None):
        selection = self.chat_listbox.curselection()
        if selection:
            previous_chat = self.current_chat
            self.current_chat = self.chat_listbox.get(selection[0])
            
            # Only update if there's a change
            if previous_chat != self.current_chat:
                self.chat_name_var.set(self.current_chat)
                
                # Clear unread message count for this chat
                self.unread_messages[self.current_chat] = 0
                self.update_chat_list_display()
                
                # Load this chat's history
                self.load_chat_history(self.current_chat)
    
    def load_chat_history(self, chat_name):
        """Load the chat history for the specified chat into the chat box"""
        self.chat_box.configure(state='normal')
        self.chat_box.delete(1.0, tk.END)
        
        for message in self.chat_histories[chat_name]:
            self.chat_box.insert(tk.END, message + '\n')
        
        self.chat_box.see(tk.END)
        self.chat_box.configure(state='disabled')
    
    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.server_ip, 12345))
            self.sock.settimeout(None)

            self.sock.sendall(self.name.encode('utf-8'))

            self.status_var.set(f"Connected to {self.server_ip} as {self.name}")
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
                msg = f"{self.name}: {message_text}"
                self.sock.sendall(msg.encode('utf-8'))
                
                # Add message to local chat history
                self.add_message_to_history("Group Chat", f"You: {message_text}")
            else:
                # Format for private message
                msg = f"@{self.current_chat}: {message_text}"
                self.sock.sendall(msg.encode('utf-8'))
                
                # Add message to local chat history
                self.add_message_to_history(self.current_chat, f"You: {message_text}")
            
            self.entry.delete(0, tk.END)
        except Exception as e:
            error_msg = f"[Error] Could not send message: {e}"
            self.add_message_to_history(self.current_chat, error_msg)
            self.status_var.set("Disconnected")
        
        return "break"  # Stops default Enter key behavior

    def add_message_to_history(self, chat_name, message):
        """Add a message to the specified chat history and update display if it's the current chat"""
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
            current_selection = self.chat_listbox.get(selected_index[0])
        
        # Remember all items
        items = [self.chat_listbox.get(i) for i in range(self.chat_listbox.size())]
        clean_items = {}
        
        # Clean up item names (remove unread count)
        for item in items:
            clean_name = item.split(" (")[0]  # Remove any " (N)" suffix
            clean_items[clean_name] = item
        
        # Update items with unread counts
        for i in range(self.chat_listbox.size()):
            item_name = self.chat_listbox.get(i).split(" (")[0]  # Get name without unread count
            unread = self.unread_messages[item_name]
            
            if unread > 0:
                new_text = f"{item_name} ({unread})"
            else:
                new_text = item_name
                
            # Only update if needed
            if self.chat_listbox.get(i) != new_text:
                self.chat_listbox.delete(i)
                self.chat_listbox.insert(i, new_text)
        
        # Restore selection
        if current_selection:
            clean_selection = current_selection.split(" (")[0]
            for i in range(self.chat_listbox.size()):
                if self.chat_listbox.get(i).startswith(clean_selection):
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

                # Handle private messages
                if msg.startswith("[Private from "):
                    # Extract sender name from "[Private from username]"
                    end_idx = msg.find("]")
                    if end_idx != -1:
                        sender = msg[len("[Private from "):]
                        sender = sender[:sender.find("]")]
                        
                        # Message without the prefix
                        content = msg[end_idx + 2:]  # +2 to skip "] "
                        
                        # Add message to the private chat history
                        self.add_message_to_history(sender, f"{sender}: {content}")
                        continue
                
                # Handle private message confirmations
                if msg.startswith("[Private to "):
                    # Extract recipient name from "[Private to username]"
                    end_idx = msg.find("]")
                    if end_idx != -1:
                        recipient = msg[len("[Private to "):]
                        recipient = recipient[:recipient.find("]")]
                        
                        # Message without the prefix
                        content = msg[end_idx + 2:]  # +2 to skip "] "
                        
                        # Add message to the private chat history
                        self.add_message_to_history(recipient, f"You: {content}")
                        continue

                # Handle system messages (join/leave notifications)
                if msg.startswith("*** "):
                    # Add to group chat
                    self.add_message_to_history("Group Chat", msg)
                    continue
                
                # Normal group message
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
            current_selection = self.chat_listbox.get(selected_index[0]).split(" (")[0]  # Remove unread count
        
        # Get current users (without unread counts)
        current_users = []
        for i in range(1, self.chat_listbox.size()):  # Skip "Group Chat"
            item = self.chat_listbox.get(i).split(" (")[0]  # Remove unread count
            current_users.append(item)
        
        # Clear all except Group Chat
        self.chat_listbox.delete(1, tk.END)
        
        # Add all users except self
        for user in usernames:
            if user and user != self.name:
                # Check if user has unread messages
                unread = self.unread_messages[user]
                if unread > 0:
                    self.chat_listbox.insert(tk.END, f"{user} ({unread})")
                else:
                    self.chat_listbox.insert(tk.END, user)
        
        # Try to restore selection
        if current_selection:
            for i in range(self.chat_listbox.size()):
                item = self.chat_listbox.get(i).split(" (")[0]  # Remove unread count
                if item == current_selection:
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