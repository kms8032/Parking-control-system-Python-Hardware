import socketio

sio = socketio.Client()

@sio.on('rpi_data')
def display_information(data):
    print("Receive Data: ", data)
    # 방향 디스플레이 표기 코드 구현

sio.connect("127.0.0.1:5002")