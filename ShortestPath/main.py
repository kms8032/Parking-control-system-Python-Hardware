import threading
import time
import queue
import yolo_tracking_deep_sort as yolo_deep_sort
import shortest_route as sr
import send_to_server as server
import socket_server
import platform
import frame_position

if platform.system() == "Linux":
    FLASK_URI = "ws://192.168.0.20:5002"
    PARKING_SPACE_PATH = "/workspace/ShortestPath/parking_space.json"
    WALKING_SPACE_PATH = "/workspace/ShortestPath/walking_space.json"
    MODEL_PATH = "/workspace/best.pt"
    VIDEO_SOURCE = 0

stop_event = threading.Event()
init_event = threading.Event()

# ---- 공유 큐 ----
yolo_data_queue = queue.Queue()
car_number_data_queue = queue.Queue()
route_data_queue = queue.Queue()
frame_queue = queue.Queue() 

# ---- 스레드 정의 ----
thread1 = threading.Thread(
    target=yolo_deep_sort.main,
    kwargs={
        "yolo_data_queue": yolo_data_queue,
        "frame_queue": frame_queue, 
        "event": init_event,
        "model_path": MODEL_PATH,
        "video_source": VIDEO_SOURCE,
    },
)

thread2 = threading.Thread(
    target=sr.main,
    kwargs={
        "yolo_data_queue": yolo_data_queue,
        "car_number_data_queue": car_number_data_queue,
        "route_data_queue": route_data_queue,
        "event": init_event,
        "parking_space_path": PARKING_SPACE_PATH,
        "walking_space_path": WALKING_SPACE_PATH,
    },
)

thread3 = threading.Thread(
    target=socket_server.get_car_number, 
    args=(car_number_data_queue,), 
    daemon=True)

thread4 = threading.Thread(
    target=server.send_to_server,
    kwargs={
        "uri": FLASK_URI,
        "route_data_queue": route_data_queue,
        "parking_space_path": PARKING_SPACE_PATH,
        "walking_space_path": WALKING_SPACE_PATH,
    },
)

thread5 = threading.Thread(
    target=frame_position.visualize_from_queue,
    args=(frame_queue, PARKING_SPACE_PATH, WALKING_SPACE_PATH),
    daemon=True,
)

# ---- 실행 ----
thread1.start()
thread2.start()
thread3.start()
thread4.start()
thread5.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("프로그램 종료 중...")
    stop_event.set()

thread1.join()
thread2.join()
thread3.join()
thread4.join()
thread5.join()
print("프로그램이 정상적으로 종료되었습니다.")