#!/usr/bin/env python3

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox
import threading
import socket

class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Chat Client")

        self.server_ip = "192.168.0.26"  # Replace with your server IP
        self.port = 12345
        self.name = simpledialog.askstring("Username", "Enter your name")
        if not self.name:
            self.name = "Anonymous"

        self.current_chat = "Group Chat"
        self.private_chats = {}  # Store ScrolledText widgets for private chats

        self.frame = tk.Frame(master)
        self.frame.pack(fill='both', expand=True)

        # Left panel for chat list (now acting like tabs)
        self.chat_list_frame = tk.Frame(self.frame)
        self.chat_list_frame.pack(side='left', fill='y')

        self.group_chat_button = tk.Button(self.chat_list_frame, text="Group Chat", command=lambda: self.change_chat("Group Chat"))
        self.group_chat_button.pack(fill='x')

        self.private_chat_buttons = {}  # Store buttons for private chats

        # Right panel to hold the current chat display
        self.right_panel = tk.Frame(self.frame)
        self.right_panel.pack(side='right', fill='both', expand=True)

        self.status_var = tk.StringVar()
        self.status_var.set("Connecting...")
        self.status_bar = tk.Label(self.right_panel, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.chat_box = ScrolledText(self.right_panel, state="disabled")  # Initial chat box for group chat
        self.chat_box.pack(fill='both', expand=True)
        self.private_chats["Group Chat"] = self.chat_box  # Store the group chat box

        self.entry = tk.Entry(self.right_panel)
        self.entry.pack(fill='x')
        self.entry.bind("<Return>", self.send_message)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.server_ip, self.port))
            self.sock.sendall(self.name.encode('utf-8'))
            self.status_var.set(f"Connected as {self.name}")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect: {e}")
            master.destroy()
            return

        threading.Thread(target=self.receive_message, daemon=True).start()

    def change_chat(self, target_chat):
        if target_chat in self.private_chats:
            # Hide the currently displayed chat
            if self.current_chat in self.private_chats and self.private_chats[self.current_chat].winfo_ismapped():
                self.private_chats[self.current_chat].pack_forget()

            # Show the selected chat
            self.private_chats[target_chat].pack(fill='both', expand=True)
            self.current_chat = target_chat
            self.entry.focus_set() # Set focus back to the entry
        else:
            # This should ideally not happen if user list updates are correct
            print(f"Error: Chat with {target_chat} not found.")

    def send_message(self, event=None):
        message_text = self.entry.get()
        if not message_text.strip():
            return

        if self.current_chat == "Group Chat":
            msg = f"{self.name}: {message_text}"
        else:
            msg = f"/pm {self.current_chat} {self.name}: {message_text}"

        try:
            self.sock.sendall(msg.encode('utf-8'))
            self.entry.delete(0, tk.END)
        except Exception as e:
            current_chat_box = self.private_chats.get(self.current_chat, self.chat_box)
            current_chat_box.configure(state='normal')
            current_chat_box.insert(tk.END, f"Error sending: {e}\n")
            current_chat_box.see(tk.END)
            current_chat_box.configure(state='disabled')

        return "break"

    def receive_message(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode('utf-8')
                if not msg:
                    break

                if msg.startswith("/users "):
                    user_list = msg[len("/users "):].split(",")
                    self.update_user_list(user_list)
                    continue

                # Check if it's a private message
                if msg.startswith("(Private)"):
                    parts = msg.split(" ", 2) # Split into "(Private)", "Sender:", "message content"
                    if len(parts) == 3:
                        sender = parts[1][:-1] # Remove the colon
                        private_message = parts[2]
                        self.display_private_message(sender, f"{sender}: {private_message}\n")
                    else:
                        self.display_message(msg + "\n", "Group Chat") # Handle unexpected format
                else:
                    self.display_message(msg + "\n", "Group Chat")

            except Exception as e:
                self.display_message(f"Error receiving: {e}\n", self.current_chat)
                break

        self.status_var.set("Disconnected from server")

    def display_message(self, message, chat_target):
        if chat_target not in self.private_chats:
            self.create_private_chat_window(chat_target)
        chat_box = self.private_chats[chat_target]
        chat_box.configure(state='normal')
        chat_box.insert(tk.END, message)
        chat_box.see(tk.END)
        chat_box.configure(state='disabled')

    def display_private_message(self, sender, message):
        if sender not in self.private_chats:
            self.create_private_chat_window(sender)
            # Optionally switch to the new private chat tab when a message arrives
            self.change_chat(sender)
        self.display_message(message, sender)

    def create_private_chat_window(self, username):
        if username not in self.private_chats:
            chat_box = ScrolledText(self.right_panel, state="disabled")
            self.private_chats[username] = chat_box
            if self.current_chat != "Group Chat" and self.current_chat != username:
                chat_box.pack_forget() # Hide new chat if not currently selected

            button = tk.Button(self.chat_list_frame, text=username, command=lambda u=username: self.change_chat(u))
            button.pack(fill='x')
            self.private_chat_buttons[username] = button

    def update_user_list(self, usernames):
        # Clear old user buttons (except Group Chat)
        for name, button in list(self.private_chat_buttons.items()):
            button.destroy()
            del self.private_chat_buttons[name]

        # Add buttons for other users
        for user in usernames:
            if user and user != self.name:
                if user not in self.private_chats:
                    self.create_private_chat_window(user)

def main():
    root = tk.Tk()
    root.geometry("800x600")
    app = ChatClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()