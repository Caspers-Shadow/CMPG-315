#!/usr/bin/env python3

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox
import threading
import socket

class ChatClientGUI:
    def __init__(self, master):  # Fixed: Changed _init_ to __init__ with double underscores
        self.master = master
        master.title("Chat Client")

        # Default settings
        self.server_ip = "192.168.0.26"  # Replace with your server IP
        self.port = 12345
        self.name = simpledialog.askstring("Username", "Enter your name")
        if not self.name:
            self.name = "Anonymous"

        # Message targets
        self.current_chat = "Group Chat"

        # Layout
        self.frame = tk.Frame(master)
        self.frame.pack(fill='both', expand=True)

        self.chat_listbox = tk.Listbox(self.frame, width=20)
        self.chat_listbox.pack(side='left', fill='y')
        self.chat_listbox.insert(tk.END, "Group Chat")
        self.chat_listbox.select_set(0)
        self.chat_listbox.bind('<<ListboxSelect>>', self.change_chat)

        self.right_panel = tk.Frame(self.frame)
        self.right_panel.pack(side='right', fill='both', expand=True)

        self.status_var = tk.StringVar()
        self.status_var.set("Connecting...")
        self.status_bar = tk.Label(self.right_panel, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.chat_box = ScrolledText(self.right_panel, state="disabled")
        self.chat_box.pack(fill='both', expand=True)

        self.entry = tk.Entry(self.right_panel)
        self.entry.pack(fill='x')
        self.entry.bind("<Return>", self.send_message)

        # Networking
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.server_ip, self.port))
            self.sock.sendall(self.name.encode('utf-8'))
            self.status_var.set(f"Connected as {self.name}")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect: {e}")
            master.destroy()
            return

        # Start receiving thread
        threading.Thread(target=self.receive_message, daemon=True).start()

    def change_chat(self, event=None):
        selection = self.chat_listbox.curselection()
        if selection:
            self.current_chat = self.chat_listbox.get(selection[0])
            self.chat_box.configure(state='normal')
            self.chat_box.insert(tk.END, f"\n--- Now chatting with {self.current_chat} ---\n")
            self.chat_box.see(tk.END)  # Ensure the message is visible
            self.chat_box.configure(state='disabled')

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
            self.chat_box.configure(state='normal')
            self.chat_box.insert(tk.END, f"Error sending: {e}\n")
            self.chat_box.see(tk.END)
            self.chat_box.configure(state='disabled')

        return "break"

    def receive_message(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode('utf-8')
                if not msg:
                    break

                # Check if it's a user list update
                if msg.startswith("/users "):
                    user_list = msg[len("/users "):].split(",")
                    self.update_user_list(user_list)
                    continue

                self.chat_box.configure(state='normal')
                self.chat_box.insert(tk.END, msg + "\n")
                self.chat_box.see(tk.END)
                self.chat_box.configure(state='disabled')
            except Exception as e:
                self.chat_box.configure(state='normal')
                self.chat_box.insert(tk.END, f"Error receiving: {e}\n")
                self.chat_box.see(tk.END)
                self.chat_box.configure(state='disabled')
                break
        
        # Update status when disconnected
        self.status_var.set("Disconnected from server")

    def update_user_list(self, usernames):
        current_selection = self.chat_listbox.curselection()  # Fixed: Use curselection instead of get(tk.ACTIVE)
        current_chat = None
        if current_selection:
            current_chat = self.chat_listbox.get(current_selection[0])
            
        self.chat_listbox.delete(1, tk.END)  # Clear old names except Group Chat
        
        for user in usernames:
            if user and user != self.name:
                self.chat_listbox.insert(tk.END, user)
                
        # Try to maintain the previous selection
        if current_chat and current_chat != "Group Chat":
            for i in range(1, self.chat_listbox.size()):
                if self.chat_listbox.get(i) == current_chat:
                    self.chat_listbox.selection_clear(0, tk.END)
                    self.chat_listbox.select_set(i)
                    break

def main():
    root = tk.Tk()
    root.geometry("800x600")
    app = ChatClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()