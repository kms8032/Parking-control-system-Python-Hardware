import time
import platform
import socketio as socketio_client

from flask import Flask, render_template, Response, stream_with_context, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
flask_sio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

# 접속한 라즈베리파이 관리 ( IP + Session ID )
clients = {}

# Express  서버로 연결할 클라이언트
express_sio = socketio_client.Client()
express_sio.connect('http://192.168.0.20:3000')

@express_sio.event
def connect():
    print('Connected to Express server')

@express_sio.event
def disconnect():
    print('Disconnected from Express server')

# 클라이언트에서 연결되었을 때 처리하는 이벤트
@flask_sio.on('connect')
def handle_connect():
	ip = request.remote_addr
	sid = request.sid
	clients[ip] = sid
	print(f"Client connected: {ip} -> {sid}")
	emit("message", {'data': 'Connected to server'})

# 클라이언트에서 보내는 기본 메세지 처리
@flask_sio.on('message')
def handle_message(data):
    print('Received message:', data)
    # 받은 데이터를 처리하거나, 필요에 따라 클라이언트에게 다시 전송할 수 있습니다.
    emit('data', {'data': data}, broadcast=True)   # broadcast=True로 설정하면 연결된 모든 클라이언트에게 전송
    express_sio.emit("vehicle_data", data) # Flask가 Express 서버로 데이터 전송

@flask_sio.on('rpi_data')
def handle_rpi_data(data):
    for target_ip, payload in data.items():
        if target_ip in clients:
            flask_sio.emit("rpi_data", payload, room=clients[target_ip])
            print(f"Sent to {target_ip} : {payload}")
        else:
            print(f"{target_ip} not connected")

# 클라이언트가 연결 해제되었을 때 처리하는 이벤트
@flask_sio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Flask-SocketIO는 일반 Flask와 다르게 socketio.run()을 사용해 서버를 실행합니다.
    flask_sio.run(app, host='0.0.0.0', port=5002, debug=True)
