import tkinter as tk
from tkinter import simpledialog, scrolledtext
import socketio
import threading

# --- CLIENT SETUP ---
sio = socketio.Client()
username = ""

# --- GUI SETUP ---
class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        master.title("Socket.IO Chat")

        self.username_frame = tk.Frame(master)
        self.username_frame.pack(pady=10)

        self.username_label = tk.Label(self.username_frame, text="Enter your username:")
        self.username_label.pack(side=tk.LEFT)

        self.username_entry = tk.Entry(self.username_frame)
        self.username_entry.pack(side=tk.LEFT)

        self.username_button = tk.Button(self.username_frame, text="Submit", command=self.submit_username)
        self.username_button.pack(side=tk.LEFT)

        # Chat UI elements (hidden until username is submitted)
        self.text_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, state='disabled', height=20, width=50)
        self.text_area.pack(padx=10, pady=10)

        self.entry = tk.Entry(master, width=40)
        self.entry.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))

        self.send_button = tk.Button(master, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(5, 10), pady=(0, 10))

    def submit_username(self):
        global username
        username = self.username_entry.get()
        if username:
            self.username_frame.pack_forget()  # Hide the username input frame
            self.text_area.configure(state='normal')
            self.text_area.insert(tk.END, f"[System] Username set to {username}.\n")
            self.text_area.configure(state='disabled')

            # Now connect to the server
            self.connect_to_server()

    def send_message(self):
        msg = self.entry.get()
        self.entry.delete(0, tk.END)

        if msg.startswith("/pm "):
            try:
                _, to_user, private_msg = msg.split(" ", 2)
                sio.emit('private_message', {'from': username, 'to': to_user, 'message': private_msg})
            except ValueError:
                self.display_message("[Error] Invalid private message format.")
        else:
            sio.emit('group_message', {'from': username, 'message': msg})

    def display_message(self, msg):
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, msg + '\n')
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def connect_to_server(self):
        try:
            sio.connect("https://new-chat-app-2wtj.onrender.com")  # Change to your deployed server URL
            sio.emit('register', username)  # Register after connecting
        except Exception as e:
            self.display_message(f"[Error] Could not connect: {e}")

    def on_close(self):
        sio.disconnect()
        self.master.destroy()


# --- SOCKET.IO EVENTS ---
@sio.event
def connect():
    gui.display_message("[System] Connected to server.")


@sio.on('message')
def on_message(data):
    gui.display_message(data)


@sio.event
def disconnect():
    gui.display_message("[System] Disconnected from server.")


def start_gui():
    global gui
    root = tk.Tk()

    gui = ChatClientGUI(root)

    # Connect to the server after username is submitted (this starts when you submit the username)
    root.protocol("WM_DELETE_WINDOW", gui.on_close)
    root.mainloop()


if __name__ == "__main__":
    start_gui()

