import socketio

sio = socketio.Client()

@sio.event()
def connect():
    print("connect")

@sio.event()
def disconnect():
    print("disconnect")

@sio.on('rpi_data')
def data(data):
    print(f"data: {data}")
    # 방향 디스플레이 구현 코드

sio.connect("http://192.168.0.20:5002")

sio.wait()
