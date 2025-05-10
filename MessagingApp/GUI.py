import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox
import threading
import socket

class ClientClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Chat Client")
        
        self.server_ip = "192.168.0.26"
            
        # Get username from user
        self.name = simpledialog.askstring("Username", "Enter your name")
        if not self.name:
            messagebox.showerror("Error", "No username provided. Using Anonymous.")
            self.name = "Anonymous"
        
        # Layout design
        self.frame = tk.Frame(master)
        self.frame.pack(fill='both', expand=True)
        
        # Left panel for chat list
        self.chat_listbox = tk.Listbox(self.frame, width=20)
        self.chat_listbox.pack(side='left', fill='y')
        
        # Add initial group chat
        self.chat_listbox.insert(tk.END, "Group Chat")
        self.chat_listbox.select_set(0)  # Chooses the Group Chat option by default
        
        # Right panel for chat messages
        self.right_panel = tk.Frame(self.frame)
        self.right_panel.pack(side='right', fill='both', expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Connecting to server...")
        self.status_bar = tk.Label(self.right_panel, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.chat_box = ScrolledText(self.right_panel, state="disabled")
        self.chat_box.pack(fill='both', expand=True)
        
        self.entry = tk.Entry(self.right_panel)
        self.entry.pack(fill='x')
        self.entry.bind("<Return>", self.send_message)
        
        # Socket setup with connection timeout
        self.connect_to_server()
    
    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)  # 5-second timeout for connection
            self.sock.connect((self.server_ip, 12345))
            self.sock.settimeout(None)  # Remove timeout for regular operation
            
            # Send username to server
            self.sock.sendall(self.name.encode('utf-8'))
            
            # Update status
            self.status_var.set(f"Connected to {self.server_ip} as {self.name}")
            
            # Start receiving thread
            threading.Thread(target=self.receive_message, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
            self.status_var.set(f"Not connected. {e}")
            self.master.after(2000, self.master.destroy)  # Close after 2 seconds
    
    def send_message(self, event=None):
        # Only proceed if there is text entered
        message_text = self.entry.get()
        if not message_text.strip():
            return  # stops sending empty messages
            
        msg = f"{self.name}: {message_text}"
        try:
            self.sock.sendall(msg.encode('utf-8'))
            self.entry.delete(0, tk.END)
        except Exception as e:
            self.chat_box.configure(state='normal')
            self.chat_box.insert(tk.END, f"Error sending message: {e}\n")
            self.chat_box.see(tk.END)
            self.chat_box.configure(state='disabled')
            self.status_var.set("Disconnected from server")
            
        return "break"  # This prevents the default behavior of adding a newline
   
    def receive_message(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode('utf-8')
                if not msg:  # Check if message is empty (connection closed)
                    self.status_var.set("Server connection closed")
                    break
                    
                self.chat_box.configure(state='normal')
                self.chat_box.insert(tk.END, msg + '\n')
                self.chat_box.see(tk.END)  # Auto-scroll to the latest message
                self.chat_box.configure(state='disabled')
            except Exception as e:
                self.chat_box.configure(state='normal')
                self.chat_box.insert(tk.END, f"Error receiving: {e}\n")
                self.chat_box.see(tk.END)
                self.chat_box.configure(state='disabled')
                self.status_var.set(f"Connection error: {e}")
                break
        
        self.status_var.set("Disconnected from server")

def main():
    root = tk.Tk()
    root.geometry("800x600")  # Set initial window size
    app = ClientClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()