# 젯슨 나노로부터 웹소켓을 이용하여 차량 번호를 수신

import time
import queue
import socketio

sio = socketio.Client(reconnection=True, reconnection_attempts=5, reconnection_delay=2)

def get_car_number(car_number_data_queue, uri):
    """젯슨 나노로부터 웹소켓을 이용하여 차량 번호를 수신하는 함수"""

    @sio.event
    def connect():
        print("WebSocket connected to", uri)

    @sio.event
    def disconnect():
        print("WebSocket disconnected")

    @sio.on("car_number")
    def handle_car_number(data):
        print("Received car number:", data)
        if data and len(data.strip()) == 4:
            car_number_data_queue.put(data)

    # 서버에 연결
    sio.connect(uri)

    # 메인 루프 (서버와 연결 유지)
    while True:
        time.sleep(1)