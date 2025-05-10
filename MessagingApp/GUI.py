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

        #Layout design
        self.frame = tk.Frame(master)
        self.frame.pack(fill = 'both', expand = True)

        #Left panel for chat list
        self.chat_listbox = tk.Listbox(self.frame, width = 20)
        self.chat_listbox.pack(side = 'left', fill = 'y')

        #Add initial group chat
        self.chat_listbox.insert(tk.END, "Group Chat")
        self.chat_listbox.select_set(0) # Chooses the Group Chat option by default

        #RIght panel for chat messages
        self.right_panel = tk.Frame(self.frame)
        self.right_panel.pack(side = 'right', fill = 'both', expand = True)

        self.chat_box = ScrolledText(self.right_panel, state = "disabled")
        self.chat_box.pack(fill = 'both', expand = True)

        self.entry = tk.Entry(self.right_panel)
        self.entry.pack(fill = 'x')
        self.entry.bind("<Return>", self.send_message)

        #Socket setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("192.168.0.38",12345)) #Place where server connections occur
        self.sock.sendall(self.name.encode('utf-8'))

        #Start receiving thread stuff
        threading.Thread(target = self.receive_message, daemon = True).start()

    def send_message(self, event = None):
        #Only proceed if there is text entered
        message_text = self.entry.get()
        if not message_text.strip():
            return #stops sending empty messages


        msg = f"{self.name}: {message_text}"
        self.sock.sendall(msg.encode('utf-8'))
        self.entry.delete(0,tk.END)

        #Display own messages immediatly
        #self.chat_box.configure(state = "normal")
        #self.chat_box.insert(tk.END, msg + "\n")
       # self.chat_box.configure(state="disabled")

        return "break"
    
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