# 각 쓰레드를 생성하고 변수를 부여하여 시작하는 메인 프로그램

import threading
from queue import Queue, Empty
import cv2
# import yolo_tracking_deep_sort as yolo_deep_sort
import yolo_tracking_bytetrack as yolo_deep_sort
import send_to_server as server
import platform
import json
import numpy as np
import flask_server
from shortest_route import Car, CarStatus
import shortest_route as sr

# 프레임에 주차 구역 및 이동 구역을 표시하는 함수
def draw_spaces(image, parking_data, moving_data):
    # 주차 구역 흰색으로 표시
    for space in parking_data.values():
        points = np.array(space["position"], np.int32)
        cv2.polylines(image, [points], isClosed=True, color=RED, thickness=2)
        centroid = points.mean(axis=0).astype(int)
        cv2.putText(image, space["name"], (centroid[0], centroid[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

    # 이동 구역 파랑색으로 표시
    for space in moving_data.values():
        points = np.array(space["position"], np.int32)
        cv2.polylines(image, [points], isClosed=True, color=BLUE, thickness=2)
        centroid = points.mean(axis=0).astype(int)
        cv2.putText(image, space["name"], (centroid[0], centroid[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, BLUE, 2)

    return image

def draw_car(frame, ltrb, car: Car):

    xmin, ymin, xmax, ymax = int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])
 
    # 주차를 위해 움직이는 차량은 초록색 사각형 및 번호 표시
    if car.status == CarStatus.ENTRY:
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), GREEN, 2)
        cv2.rectangle(frame, (xmin, ymin - 35), (xmin + 75, ymin), GREEN, -1)
        cv2.putText(frame, str(car.car_number), (xmin + 5, ymin - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, WHITE, 2)
    
    # 주차한 차량은 빨강색 사각형 및 번호 표시
    elif car.status == CarStatus.PARKING:
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), RED, 2)
        cv2.rectangle(frame, (xmin, ymin - 35), (xmin + 75, ymin), RED, -1)
        cv2.putText(frame, str(car.car_number), (xmin + 5, ymin - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, WHITE, 2)

    # 출차를 위해 움직이는 차량은 노랑색 사각형 및 번호 표시
    else:
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), YELLOW, 2)
        cv2.rectangle(frame, (xmin, ymin - 35), (xmin + 75, ymin), YELLOW, -1)
        cv2.putText(frame, str(car.car_number), (xmin + 5, ymin - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, WHITE, 2)

def load_json(filename):
    with open(filename, 'r') as file:
        return json.load(file)


RED = (0, 0, 255)
WHITE = (255, 255, 255)
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (0, 255, 255)

if platform.system() == "Darwin":
    # 서버 주소 및 포트 (Socket.IO)
    URI = "http://127.0.0.1:3000"
    # 주차 구역 좌표 파일 경로
    PARKING_SPACE_PATH = "/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/position_file/parking_space.json"
    # 이동 구역 좌표 파일 경로
    MOVING_SPACE_PATH = "/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/position_file/moving_space.json"
    # YOLO 모델 경로
    MODEL_PATH = "/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/model/v2_best_small.pt"
    # 비디오 소스
    VIDEO_SOURCE = 0

    FRAME_WIDTH = 1080
    FRAME_HEIGHT = 560

elif platform.system() == "Windows":
    # 서버 주소 및 포트
    URI = "http://127.0.0.1:5002"
    # 주차 구역 좌표 파일 경로
    PARKING_SPACE_PATH = "/workspace/Parking-control-system-Python-Hardware-main/ShortestPath/position_file/parking_space.json"
    # 이동 구역 좌표 파일 경로
    MOVING_SPACE_PATH = "/workspace/Parking-control-system-Python-Hardware-main/ShortestPath/position_file/moving_space.json"
    # YOLO 모델 경로
    MODEL_PATH = "/workspace/best.pt"
    # 비디오 소스
    VIDEO_SOURCE = 0

    FRAME_WIDTH = 1920
    FRAME_HEIGHT = 1080

else:   # Linux (Jetson)
    # 서버 주소 및 포트 (Socket.IO)
    URI = "http://192.168.0.48:3000"
    # 주차 구역 좌표 파일 경로
    PARKING_SPACE_PATH = "/workspace/ShortestPath/position_file/parking_space.json"
    # 이동 구역 좌표 파일 경로
    MOVING_SPACE_PATH = "/workspace/ShortestPath/position_file/moving_space.json"
    # YOLO 모델 경로
    MODEL_PATH = "/workspace/ShortestPath/model/best.pt"
    # 비디오 소스
    VIDEO_SOURCE = 0

    FRAME_WIDTH = 1920
    FRAME_HEIGHT = 1080

# 프로그램 종료 플래그
stop_event = threading.Event()
init_event = threading.Event()

# 공유할 데이터 큐
yolo_data_queue = Queue()
car_number_data_queue = Queue()
car_number_response_queue = Queue() # 입차기에 응답할 데이터
route_data_queue = Queue()
frame_queue = Queue(maxsize=2)    # gui에 표시할 이미지
id_match_car_number_queue: Queue[dict[int, Car]] = Queue(maxsize=2)
exit_queue = Queue()

# 쓰레드 생성
thread1 = threading.Thread(
    target=yolo_deep_sort.main, 
    kwargs={
        "yolo_data_queue": yolo_data_queue, 
        "frame_queue": frame_queue, 
        "event": init_event, 
        "model_path": MODEL_PATH, 
        "video_source": VIDEO_SOURCE,
        "frame_width": FRAME_WIDTH,
        "frame_height": FRAME_HEIGHT,
        "stop_event": stop_event, # 성능 체크
    }
)

thread2 = threading.Thread(
    target=sr.main, 
    kwargs={
        "yolo_data_queue": yolo_data_queue, 
        "car_number_data_queue": car_number_data_queue, 
        "route_data_queue": route_data_queue, 
        "event": init_event, 
        "parking_space_path": PARKING_SPACE_PATH, 
        "moving_space_path": MOVING_SPACE_PATH, 
        "id_match_car_number_queue": id_match_car_number_queue,
        "car_number_response_queue": car_number_response_queue,
        "exit_queue": exit_queue,
    }
)

thread3 = threading.Thread(
    target=flask_server.run_flask_server,
    kwargs={
        "car_number_data_queue": car_number_data_queue,
        "response_data_queue": car_number_response_queue,
    }
)

thread4 = threading.Thread(
    target=server.send_to_server, 
    kwargs={
        "uri": URI, 
        "route_data_queue": route_data_queue,
        "exit_queue": exit_queue,
    }
)

# 쓰레드 시작
thread1.start()
thread2.start()
thread3.start()
thread4.start()

parking_data = load_json(PARKING_SPACE_PATH)
moving_data = load_json(MOVING_SPACE_PATH)

try:
    # 메인 루프에서 프레임을 받아 GUI 표시
    car_numbers = {}
    while True:
        try:
            if not id_match_car_number_queue.empty():
                car_numbers = id_match_car_number_queue.get_nowait()

            frame, tracks = frame_queue.get(timeout=0.1)

            # 구역 작성
            frame_with_space = draw_spaces(frame, parking_data, moving_data)

            # 탐지한 객체 루프
            for track in tracks:
                if not track.is_confirmed():
                    continue
                track_id = int(track.track_id)
                if track_id in car_numbers:
                    draw_car(frame_with_space, track.to_ltrb(), car_numbers[track_id])

            # 젯슨 환경에서 GUI 사이즈 조절을 위해 필요
            cv2.namedWindow("YOLO Tracking", cv2.WINDOW_NORMAL)

            # GUI 표시
            cv2.imshow("YOLO Tracking", frame_with_space)

            # 키 입력 처리 (1ms 대기)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("'q' 키 입력 - 프로그램 종료 중...")
                stop_event.set()
                break

        except Empty:
            # 프레임이 없으면 계속 대기
            continue

except KeyboardInterrupt:
    # 키보드 인터럽트 발생 시 쓰레드 종료
    print("프로그램 종료 중...")
    stop_event.set()

# OpenCV 윈도우 정리
cv2.destroyAllWindows()

# 모든 쓰레드가 종료될 때까지 대기
thread1.join()
thread2.join()
thread3.join()
thread4.join()

print("프로그램이 정상적으로 종료되었습니다.")
