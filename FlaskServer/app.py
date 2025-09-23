import time
import platform
import socketio

from flask import Flask, render_template, Response, stream_with_context
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

express_sio = socketio.Client()
express_sio.connect('http://localhost:3000')

@express_sio.event
def connect():
    print('Connected to Express server')

@express_sio.event
def disconnect():
    print('Disconnected from Express server')

# 클라이언트에서 연결되었을 때 처리하는 이벤트
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('message', {'data': 'Connected to server!'})

# 클라이언트에서 보내는 기본 메세지 처리
@socketio.on('message')
def handle_message(data):
    print('Received message:', data)
    # 받은 데이터를 처리하거나, 필요에 따라 클라이언트에게 다시 전송할 수 있습니다.
    emit('data', {'data': data}, broadcast=True)   # broadcast=True로 설정하면 연결된 모든 클라이언트에게 전송
    express_sio.emit("ai_result", data)

# 클라이언트가 연결 해제되었을 때 처리하는 이벤트
@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Flask-SocketIO는 일반 Flask와 다르게 socketio.run()을 사용해 서버를 실행합니다.
    if platform.system() == "Linux":
        socketio.run(app, host='0.0.0.0', port=5002, debug=True)
    else:
        socketio.run(app, host='127.0.0.1', port=5002, debug=True)
