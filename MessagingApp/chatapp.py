import sys
import threading
import socket
import json
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QDialog, QGridLayout, QScrollArea)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor

# Global variables
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555
client_socket = None
client_name = ""

# Server code (from server.py)
class ChatServer:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.running = False
        
    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"Server started on {self.host}:{self.port}")
            self.running = True
            
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            return True
        except Exception as e:
            print(f"Server error: {e}")
            return False
    
    def stop(self):
        self.running = False
        # Close all client connections
        for client in list(self.clients.values()):
            try:
                client.close()
            except:
                pass
        # Close server socket
        try:
            self.server_socket.close()
        except:
            pass
        print("Server stopped")
    
    def accept_connections(self):
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, 
                                               args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()
            except:
                if self.running:  # Only show error if we didn't stop the server intentionally
                    print("Error accepting connection")
                break
    
    def handle_client(self, client_socket):
        try:
            # Get the client's name
            name_data = client_socket.recv(1024).decode('utf-8')
            name = json.loads(name_data)['name']
            
            # Add client to our dictionary
            self.clients[name] = client_socket
            
            # Notify all clients that a new client has joined
            self.broadcast({"type": "system", "message": f"{name} has joined the chat!"})
            
            # Send the list of current users to the new client
            users_list = list(self.clients.keys())
            client_socket.send(json.dumps({"type": "users_list", "users": users_list}).encode('utf-8'))
            
            # Handle messages from the client
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    message_data = json.loads(data)
                    
                    # Broadcast the message to all clients
                    if message_data.get('type') == 'message':
                        self.broadcast(message_data)
                except:
                    break
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            # Remove client from dictionary and close the socket
            if name in self.clients:
                del self.clients[name]
                client_socket.close()
                # Notify all clients that a client has left
                self.broadcast({"type": "system", "message": f"{name} has left the chat!"})
    
    def broadcast(self, message_dict):
        """Send a message to all connected clients"""
        message_json = json.dumps(message_dict)
        disconnected_clients = []
        
        for client_name, client_socket in self.clients.items():
            try:
                client_socket.send(message_json.encode('utf-8'))
            except:
                # If we can't send to this client, mark it for removal
                disconnected_clients.append(client_name)
        
        # Remove any disconnected clients
        for name in disconnected_clients:
            if name in self.clients:
                del self.clients[name]

# GUI code (from GUI.py)
class SignalHandler(QObject):
    message_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    users_list_updated = pyqtSignal(list)
    server_status_changed = pyqtSignal(bool, str)

signal_handler = SignalHandler()

class LoginDialog(QDialog):
    def __init__(self, current_host=SERVER_HOST, current_port=SERVER_PORT, current_name=""):
        super().__init__()
        self.setWindowTitle("Connection Settings")
        self.setFixedSize(400, 200)
        
        layout = QGridLayout()
        
        self.name_label = QLabel("Username:")
        self.name_input = QLineEdit(current_name)
        self.name_input.setPlaceholderText("Enter your username")
        
        self.server_label = QLabel("Server Address:")
        self.server_input = QLineEdit(current_host)
        self.server_input.setPlaceholderText("e.g., 127.0.0.1 or server IP")
        
        # Add a button to use local IP
        self.local_ip_button = QPushButton("Use My IP")
        self.local_ip_button.clicked.connect(self.use_local_ip)
        
        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit(str(current_port))
        self.port_input.setPlaceholderText("e.g., 5555")
        
        # Add help text
        self.help_text = QLabel("To host a server: Use your IP or 0.0.0.0 as server address")
        self.help_text.setWordWrap(True)
        self.help_text2 = QLabel("To connect: Use the IP address of the server computer")
        self.help_text2.setWordWrap(True)
        
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        # Add widgets to layout
        layout.addWidget(self.name_label, 0, 0)
        layout.addWidget(self.name_input, 0, 1, 1, 2)
        
        layout.addWidget(self.server_label, 1, 0)
        layout.addWidget(self.server_input, 1, 1)
        layout.addWidget(self.local_ip_button, 1, 2)
        
        layout.addWidget(self.port_label, 2, 0)
        layout.addWidget(self.port_input, 2, 1, 1, 2)
        
        layout.addWidget(self.help_text, 3, 0, 1, 3)
        layout.addWidget(self.help_text2, 4, 0, 1, 3)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout, 5, 0, 1, 3)
        
        self.setLayout(layout)
    
    def use_local_ip(self):
        """Get and use the local IP address"""
        try:
            # Create a socket that connects to an external server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # This doesn't actually create a connection, but allows us to get local IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self.server_input.setText(ip)
        except:
            # If there's an error, use a sensible default
            self.server_input.setText("0.0.0.0")
    
    def get_login_info(self):
        port_str = self.port_input.text()
        try:
            port = int(port_str)
        except ValueError:
            port = 5555  # Default if invalid
            
        return {
            "name": self.name_input.text(),
            "server": self.server_input.text(),
            "port": port
        }

class ChatClientApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Chat Application")
        self.setGeometry(100, 100, 800, 600)
        
        self.server = None
        self.server_running = False
        self.username = "User"  # Default username
        self.is_connected = False
        
        self.setup_ui()
        self.connect_signals()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_connection)
        self.timer.start(5000)  # Check connection every 5 seconds
        
        # Show initial welcome message
        self.display_message("Welcome to the Chat Application!")
        self.display_message("Please use 'Connection Settings' to set your username and server details.")
        self.display_message("Start the server first, then connect to it.")
        
        # No automatic login dialog at startup
        # Let user explicitly choose when to configure and connect
    
    def setup_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Chat area
        chat_layout = QVBoxLayout()
        
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        chat_layout.addWidget(self.chat_area)
        
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        chat_layout.addLayout(input_layout)
        
        # Users area
        users_layout = QVBoxLayout()
        users_label = QLabel("Online Users")
        users_label.setAlignment(Qt.AlignCenter)
        users_layout.addWidget(users_label)
        
        self.users_list = QTextEdit()
        self.users_list.setReadOnly(True)
        self.users_list.setFixedWidth(200)
        users_layout.addWidget(self.users_list)
        
        # Server controls
        server_controls_layout = QVBoxLayout()
        
        # Connection status
        self.connection_status = QLabel("Connection: Disconnected")
        server_controls_layout.addWidget(self.connection_status)
        
        # Server status
        self.status_label = QLabel("Server: Offline")
        server_controls_layout.addWidget(self.status_label)
        
        # Server controls
        server_buttons_layout = QHBoxLayout()
        self.start_server_button = QPushButton("Start Server")
        self.start_server_button.clicked.connect(self.toggle_server)
        server_buttons_layout.addWidget(self.start_server_button)
        
        # Connect button
        self.connect_button = QPushButton("Connect to Server")
        self.connect_button.clicked.connect(self.connect_to_server)
        server_buttons_layout.addWidget(self.connect_button)
        
        server_controls_layout.addLayout(server_buttons_layout)
        
        # Settings button
        self.settings_button = QPushButton("Connection Settings")
        self.settings_button.clicked.connect(self.show_login_dialog)
        server_controls_layout.addWidget(self.settings_button)
        
        users_layout.addLayout(server_controls_layout)
        
        # Main layout arrangement
        main_layout.addLayout(chat_layout)
        main_layout.addLayout(users_layout)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def connect_signals(self):
        signal_handler.message_received.connect(self.display_message)
        signal_handler.connection_status.connect(self.update_connection_status)
        signal_handler.users_list_updated.connect(self.update_users_list)
        signal_handler.server_status_changed.connect(self.handle_server_status_change)
    
    def show_login_dialog(self):
        dialog = LoginDialog()
        if dialog.exec_():
            login_info = dialog.get_login_info()
            
            # Validate inputs
            if not login_info["name"].strip():
                self.display_message("Error: Username cannot be empty")
                QTimer.singleShot(500, self.show_login_dialog)
                return
                
            self.username = login_info["name"]
            
            global SERVER_HOST, SERVER_PORT
            SERVER_HOST = login_info["server"]
            SERVER_PORT = login_info["port"]
            
            self.setWindowTitle(f"Chat Application - {self.username}")
            self.status_label.setText(f"Server: {SERVER_HOST}:{SERVER_PORT}")
            self.connect_to_server()
        else:
            # User cancelled login
            self.display_message("Please login to connect to the chat server.")
            
    def handle_server_status_change(self, is_running, server_address):
        if is_running:
            # Update the server status UI elements
            self.start_server_button.setText("Stop Server")
            self.status_label.setText(f"Server: Online ({server_address})")
        else:
            # Update the server status UI elements
            self.start_server_button.setText("Start Server")
            self.status_label.setText("Server: Offline")
    
    def toggle_server(self):
        if not self.server_running:
            try:
                # Test if the port is already in use
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.settimeout(1)
                result = test_socket.connect_ex((SERVER_HOST, SERVER_PORT))
                test_socket.close()
                
                if result == 0:
                    # Port is already in use
                    self.display_message(f"Port {SERVER_PORT} is already in use. Cannot start server.")
                    self.status_label.setText(f"Server: Error (Port {SERVER_PORT} in use)")
                    return
                    
                self.server = ChatServer(SERVER_HOST, SERVER_PORT)
                if self.server.start():
                    self.server_running = True
                    self.start_server_button.setText("Stop Server")
                    self.status_label.setText(f"Server: Online ({SERVER_HOST}:{SERVER_PORT})")
                    self.display_message(f"Server started on {SERVER_HOST}:{SERVER_PORT}")
                    signal_handler.server_status_changed.emit(True, f"{SERVER_HOST}:{SERVER_PORT}")
            except Exception as e:
                self.display_message(f"Failed to start server: {e}")
                self.status_label.setText("Server: Error")
                if self.server:
                    try:
                        self.server.stop()
                    except:
                        pass
                    self.server = None
        else:
            if self.server:
                self.server.stop()
                self.server = None
                self.server_running = False
                self.start_server_button.setText("Start Server")
                self.status_label.setText("Server: Offline")
                self.display_message("Server stopped")
                signal_handler.server_status_changed.emit(False, "")
    
    def connect_to_server(self):
        global client_socket, client_name
        
        # Don't try to connect if no username is set
        if not self.username or self.username == "User":
            self.display_message("Please set your username in Connection Settings first.")
            self.show_login_dialog()
            return
            
        # If already connected, disconnect first
        if self.is_connected and client_socket:
            try:
                client_socket.close()
            except:
                pass
            self.is_connected = False
            self.connection_status.setText("Connection: Disconnected")
            self.display_message("Disconnected from server")
            self.connect_button.setText("Connect to Server")
            return
        
        try:
            # Create new socket and connect
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)  # 5 second timeout for connection
            self.display_message(f"Attempting to connect to {SERVER_HOST}:{SERVER_PORT}...")
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            client_socket.settimeout(None)  # Reset timeout for normal operation
            
            # Send username to server
            client_name = self.username
            client_socket.send(json.dumps({"name": client_name}).encode('utf-8'))
            
            # Start thread to receive messages
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Update UI
            self.is_connected = True
            signal_handler.connection_status.emit(True)
            self.connect_button.setText("Disconnect")
            self.display_message(f"Connected to server at {SERVER_HOST}:{SERVER_PORT}")
            
        except socket.timeout:
            self.display_message("Connection timed out. Server may be unreachable.")
            signal_handler.connection_status.emit(False)
            if client_socket:
                client_socket.close()
                
        except ConnectionRefusedError:
            self.display_message(f"Connection refused to {SERVER_HOST}:{SERVER_PORT}. Make sure the server is running.")
            # Suggest starting the server if trying to connect locally
            if SERVER_HOST in ('127.0.0.1', 'localhost', self.get_local_ip()):
                self.display_message("Would you like to start the server now? Click 'Start Server' button.")
            signal_handler.connection_status.emit(False)
            if client_socket:
                client_socket.close()
                
        except Exception as e:
            self.display_message(f"Error connecting to server: {e}")
            signal_handler.connection_status.emit(False)
            if client_socket:
                client_socket.close()
    
    def receive_messages(self):
        global client_socket
        
        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message_data = json.loads(data)
                
                if message_data.get('type') == 'users_list':
                    signal_handler.users_list_updated.emit(message_data.get('users', []))
                elif message_data.get('type') == 'system':
                    signal_handler.message_received.emit(f"[SYSTEM] {message_data.get('message', '')}")
                elif message_data.get('type') == 'message':
                    sender = message_data.get('sender', 'Unknown')
                    message = message_data.get('message', '')
                    signal_handler.message_received.emit(f"[{sender}] {message}")
            except:
                # If we can't receive messages, assume we're disconnected
                signal_handler.connection_status.emit(False)
                signal_handler.message_received.emit("Disconnected from server")
                break
    
    def send_message(self):
        message = self.message_input.text().strip()
        if message and client_socket:
            try:
                message_data = {
                    "type": "message",
                    "sender": client_name,
                    "message": message
                }
                client_socket.send(json.dumps(message_data).encode('utf-8'))
                self.message_input.clear()
            except:
                self.display_message("Failed to send message, may be disconnected")
                signal_handler.connection_status.emit(False)
    
    def display_message(self, message):
        self.chat_area.append(message)
        # Auto-scroll to bottom
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_area.setTextCursor(cursor)
    
    def update_connection_status(self, connected):
        self.is_connected = connected
        if connected:
            self.connection_status.setText("Connection: Connected")
            self.connect_button.setText("Disconnect")
        else:
            self.connection_status.setText("Connection: Disconnected")
            self.connect_button.setText("Connect to Server")
            
    def get_local_ip(self):
        """Get the local IP address of this machine"""
        try:
            # Create a socket that connects to an external server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # This doesn't actually create a connection, but allows us to get local IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"  # Fallback to localhost
    
    def update_users_list(self, users):
        self.users_list.clear()
        for user in users:
            self.users_list.append(user)
    
    def check_connection(self):
        global client_socket
        if client_socket:
            try:
                # Try to send a ping to check if we're still connected
                client_socket.send(json.dumps({"type": "ping"}).encode('utf-8'))
            except:
                signal_handler.connection_status.emit(False)
    
    def closeEvent(self, event):
        global client_socket
        # Clean up resources when closing the application
        if self.server and self.server_running:
            self.server.stop()
        
        if client_socket:
            try:
                client_socket.close()
            except:
                pass
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    window = ChatClientApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()