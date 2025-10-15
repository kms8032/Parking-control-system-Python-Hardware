# 젯슨 나노로부터 웹소켓을 이용하여 차량 번호를 수신
import socketio
import eventlet

# Socket.IO 서버 초기화
sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)

def get_car_number(car_number_data_queue):
    """젯슨 나노로부터 차량 번호를 수신하여 큐에 저장"""

    @sio.on("connect")
    def connect(sid, environ):
        print("WebSocket connected:", sid)

    @sio.on("disconnect")
    def disconnect(sid):
        print("WebSocket disconnected:", sid)

    @sio.on("car_number")
    def handle_car_number(sid, data):
        print("Received car number:", data)
        if data and len(data.strip()) == 4:
            car_number_data_queue.put(data.strip())
            print(f"Queue 저장 완료: {data.strip()}")
        else:
            print("유효하지 않은 차량 번호 수신:", data)

    print("Socket.IO server running on 0.0.0.0:5003")
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5003)), app)