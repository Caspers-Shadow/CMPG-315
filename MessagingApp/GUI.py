import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog
import threading
import socket

class ClientClientGUI:
    def __init__(self,master):
        self.name = simpledialog.askstring("Username", "Enter your name")
        self.master = master
        master.title("Chat Client")

        self.chat_box = ScrolledText(master,state = "disabled")
        self.chat_box.pack()

        self.entry = tk.Entry(master)
        self.entry.pack(fill = 'x')
        self.entry.bind("<Return>", self.send_message)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("192.168.0.38",12345))

        #Send username data first
        self.sock.sendall(self.name.encode('utf-8'))

        #Start receiving thread
        threading.Thread(target = self.receive_message, daemon = True).start()

    def send_message(self, event = None):
        msg = f"{self.name}: {self.entry.get()}"
        self.sock.sendall(msg.encode('utf-8'))
        self.entry.delete(0,tk.END)

        #Display own messages immediatly
        self.chat_box.configure(state = "normal")
        self.chat_box.insert(tk.END, message + "\n")
        self.chat_box.configure(state="disabled")
    
    def receive_message(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode('utf-8')
                self.chat_box.configure(state = 'normal')
                self.chat_box.insert(tk.END, msg + '\n')
                self.chat_box.configure(state = 'disabled')
            except:
                break
    
root = tk.Tk()
app = ClientClientGUI(root)
root.mainloop()