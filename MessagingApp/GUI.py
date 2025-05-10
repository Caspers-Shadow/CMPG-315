import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox
import threading
import socket

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

        self.chat_listbox = tk.Listbox(self.frame, width=20)
        self.chat_listbox.pack(side='left', fill='y')
        self.chat_listbox.insert(tk.END, "Group Chat")
        self.chat_listbox.select_set(0)

        self.right_panel = tk.Frame(self.frame)
        self.right_panel.pack(side='right', fill='both', expand=True)

        self.status_var = tk.StringVar()
        self.status_var.set("Connecting to server...")
        self.status_bar = tk.Label(self.right_panel, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.chat_box = ScrolledText(self.right_panel, state="disabled")
        self.chat_box.pack(fill='both', expand=True)

        self.entry = tk.Entry(self.right_panel)
        self.entry.pack(fill='x')
        self.entry.bind("<Return>", self.send_message)

        self.connect_to_server()
    
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

        selected_chat = self.chat_listbox.get(tk.ACTIVE)
        if selected_chat == "Group Chat":
            msg = f"{self.name}: {message_text}"
        else:
            msg = f"@{selected_chat}: {message_text}"

        try:
            self.sock.sendall(msg.encode('utf-8'))
            self.entry.delete(0, tk.END)
        except Exception as e:
            self.chat_box.configure(state='normal')
            self.chat_box.insert(tk.END, f"[Error] Could not send message: {e}\n")
            self.chat_box.see(tk.END)
            self.chat_box.configure(state='disabled')
            self.status_var.set("Disconnected")
        return "break"

    def receive_message(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode('utf-8')
                if not msg:
                    self.status_var.set("Server connection closed")
                    break

                self.chat_box.configure(state='normal')
                self.chat_box.insert(tk.END, msg + '\n')
                self.chat_box.see(tk.END)
                self.chat_box.configure(state='disabled')

                # Optional: Auto-add usernames mentioned in private messages
                if msg.startswith("[Private]"):
                    parts = msg.split()
                    if len(parts) >= 2:
                        sender = parts[1][:-1]
                        if sender != self.name and sender not in self.chat_listbox.get(0, tk.END):
                            self.chat_listbox.insert(tk.END, sender)

            except Exception as e:
                self.chat_box.configure(state='normal')
                self.chat_box.insert(tk.END, f"[Error receiving] {e}\n")
                self.chat_box.see(tk.END)
                self.chat_box.configure(state='disabled')
                break
        self.status_var.set("Disconnected from server")

def main():
    root = tk.Tk()
    root.geometry("800x600")
    app = ClientClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()