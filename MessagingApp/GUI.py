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
        
        # Flag to prevent double processing of sent messages
        self.message_sent = False

        # Initialize chat history with welcome messages
        self.chat_histories["Group Chat"].append("--- Welcome to Group Chat ---")
        
        # Load initial chat history
        self.load_chat_history("Group Chat")

        self.connect_to_server()
    
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