# --- SERVER SECTION ---
from flask import Flask, request
from flask_socketio import SocketIO, emit
import threading
import socketio
import time
import os

app = Flask(__name__)
socketio_server = SocketIO(app, cors_allowed_origins="*")

connected_users = {}  # username -> session ID


@app.route('/')
def index():
    return "Chat server is up."


@socketio_server.on('register')
def register(username):
    connected_users[username] = request.sid
    print(f"{username} registered with SID {request.sid}")


@socketio_server.on('disconnect')
def on_disconnect():
    for user, sid in list(connected_users.items()):
        if sid == request.sid:
            del connected_users[user]
            print(f"{user} disconnected")
            break


@socketio_server.on('group_message')
def handle_group(data):
    msg = f"[Group] {data['from']}: {data['message']}"
    print(msg)
    emit('message', msg, broadcast=True)


@socketio_server.on('private_message')
def handle_private(data):
    recipient = data['to']
    msg = f"[Private] {data['from']} to {recipient}: {data['message']}"
    print(msg)
    if recipient in connected_users:
        emit('message', msg, to=connected_users[recipient])
    else:
        emit('message', f"[Server] {recipient} is not online.", to=request.sid)


def run_server():
    port = int(os.environ.get("PORT",10000))
    socketio_server.run(app, host = "0.0.0.0", port = port)

# --- TEST CLIENT SECTION (for local testing only) ---
def run_test_client(username):
    sio = socketio.Client()

    @sio.event
    def connect():
        print(f"{username} connected to server.")
        sio.emit('register', username)

    @sio.on('message')
    def message(data):
        print(f"{username} received:", data)

    sio.connect("https://new-chat-app-2wtj.onrender.com")  # <-- CHANGE THIS TO RENDER URL WHEN DEPLOYED

    def send_loop():
        while True:
            msg = input(f"[{username}] Enter message ('/pm user message' or plain text): ")
            if msg.startswith("/pm "):
                _, to_user, private_msg = msg.split(" ", 2)
                sio.emit('private_message', {'from': username, 'to': to_user, 'message': private_msg})
            else:
                sio.emit('group_message', {'from': username, 'message': msg})

    threading.Thread(target=send_loop).start()
    sio.wait()


if __name__ == '__main__':
    username = input("Enter your username: ")
    run_test_client(username)  
