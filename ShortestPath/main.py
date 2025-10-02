# 각 쓰레드를 생성하고 변수를 부여하여 시작하는 메인 프로그램

import threading
import time
import queue
import yolo_tracking_deep_sort as yolo_deep_sort
import shortest_route as sr
import send_to_server as server
import uart
import platform

if platform.system() == "Darwin":
    # 서버 주소 및 포트
    FLASK_URI = "ws://127.0.0.1:5002"
    # 주차 구역 좌표 파일 경로
    PARKING_SPACE_PATH = "/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/position_file/parking_space.json"
    # 이동 구역 좌표 파일 경로
    WALKING_SPACE_PATH = "/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/position_file/walking_space.json"
    # YOLO 모델 경로
    MODEL_PATH = "/Users/kyumin/python-application/carDetection/PCS-model/yolov8_v3/weights/best.pt"
    # 비디오 소스
    VIDEO_SOURCE = 0
elif platform.system() == "Linux":
    # 서버 주소 및 포트
    FLASK_URI = "ws://192.168.0.41:5002"
    # 주차 구역 좌표 파일 경로
    PARKING_SPACE_PATH = "/workspace/Parking-control-system-Python-Hardware-main/ShortestPath/position_file/parking_space.json"
    # 이동 구역 좌표 파일 경로
    WALKING_SPACE_PATH = "/workspace/Parking-control-system-Python-Hardware-main/ShortestPath/position_file/walking_space.json"
    # YOLO 모델 경로
    MODEL_PATH = "/workspace/best.pt"
    # 비디오 소스
    VIDEO_SOURCE = 0
elif platform.system() == "Windows":
    # 서버 주소 및 포트
    FLASK_URI = "http://127.0.0.1:5002"
    # 주차 구역 좌표 파일 경로
    PARKING_SPACE_PATH = "/workspace/Parking-control-system-Python-Hardware-main/ShortestPath/position_file/parking_space.json"
    # 이동 구역 좌표 파일 경로
    WALKING_SPACE_PATH = "/workspace/Parking-control-system-Python-Hardware-main/ShortestPath/position_file/walking_space.json"
    # YOLO 모델 경로
    MODEL_PATH = "/workspace/best.pt"
    # 비디오 소스
    VIDEO_SOURCE = 0

# 프로그램 종료 플래그
stop_event = threading.Event()
init_event = threading.Event()

# 공유할 데이터 큐
yolo_data_queue = queue.Queue()
car_number_data_queue = queue.Queue()
route_data_queue = queue.Queue()

# 쓰레드 생성
thread1 = threading.Thread(target=yolo_deep_sort.main, kwargs={"yolo_data_queue": yolo_data_queue, "event": init_event, "model_path": MODEL_PATH, "video_source": VIDEO_SOURCE})
thread2 = threading.Thread(target=sr.main, kwargs={"yolo_data_queue": yolo_data_queue, "car_number_data_queue": car_number_data_queue, "route_data_queue": route_data_queue, "event": init_event, "parking_space_path": PARKING_SPACE_PATH, "walking_space_path": WALKING_SPACE_PATH})
thread3 = threading.Thread(target=uart.get_car_number, kwargs={"uri": FLASK_URI, "car_number_data_queue": car_number_data_queue})
thread4 = threading.Thread(target=server.send_to_server, kwargs={"uri": FLASK_URI, "route_data_queue": route_data_queue, "parking_space_path": PARKING_SPACE_PATH, "walking_space_path": WALKING_SPACE_PATH})

# 쓰레드 시작
thread1.start()
thread2.start()
thread3.start()
thread4.start()

try:
    # 메인 프로그램을 무한 대기 상태로 유지
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # 키보드 인터럽트 발생 시 쓰레드 종료
    print("프로그램 종료 중...")
    stop_event.set()

# 모든 쓰레드가 종료될 때까지 대기
thread1.join()
thread2.join()
thread3.join()
thread4.join()

print("프로그램이 정상적으로 종료되었습니다.")
