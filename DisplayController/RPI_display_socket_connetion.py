import socketio

sio = socketio.Client()

@sio.event()
def connect():
    print("connect")

@sio.event()
def disconnect():
    print("disconnect")

@sio.on('rpi_data')
#def catch_all(event, data=None):
   # print(f"Data: {event}, data: {data}")
   # print("Receive Data: ", data)
    # 방향 디스플레이 표기 코드 구
def data(data):
    print(f"data: {data}")

sio.connect("http://192.168.0.20:5002")

sio.wait()
