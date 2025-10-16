# 작성한 좌표를 시각적으로 확인하는 코드

import json
import cv2
import numpy as np
import platform
from deep_sort_realtime.deepsort_tracker import DeepSort
from ultralytics import YOLO
import torch

# Define colors
RED = (0, 0, 255)
WHITE = (255, 255, 255)
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (0, 255, 255)


# Function to load JSON data from a file
def load_json(filename):
    with open(filename, 'r') as file:
        return json.load(file)


# Function to draw parking and walking spaces on an image
def draw_spaces(image, parking_data, walking_data):
    # Draw parking spaces in white
    for space in parking_data.values():
        points = np.array(space["position"], np.int32)
        cv2.polylines(image, [points], isClosed=True, color=RED, thickness=2)
        centroid = points.mean(axis=0).astype(int)
        cv2.putText(image, space["name"], (centroid[0], centroid[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

    # Draw walking spaces in blue
    for space in walking_data.values():
        points = np.array(space["position"], np.int32)
        cv2.polylines(image, [points], isClosed=True, color=BLUE, thickness=2)
        centroid = points.mean(axis=0).astype(int)
        cv2.putText(image, space["name"], (centroid[0], centroid[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, BLUE, 2)

    return image


# Function to check if a point is within any defined space with a buffer
def check_point_in_space(point, parking_spaces_data, walking_space_data, buffer=1):  # 버퍼를 1로 조정
    for space_name, space in parking_spaces_data.items():
        # 공간 이름을 출력하여 확인
        print(f"Checking {space_name} for point {point}")
        if is_point_in_rectangle(point, space["position"]):
            print(f"Point {point} is inside {space['name']}")
            return space["name"]

    for space_name, space in walking_space_data.items():
        # 공간 이름을 출력하여 확인
        print(f"Checking {space_name} for point {point}")
        if is_point_in_rectangle(point, space["position"]):
            print(f"Point {point} is inside {space['name']}")
            return space["name"]

    return None


def is_point_in_rectangle(point, rectangle):
    """
    특정 좌표가 사각형 내부에 있는지 확인하는 함수.

    Args:
        point: (x, y) 확인할 좌표
        rectangle: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] 사각형의 꼭짓점 (좌상단, 우상단, 우하단, 좌하단 순서)
    Return:
        bool 해당 점이 사각형 안에 있는지 여부
    """

    def vector_cross_product(v1, v2):
        """두 벡터의 외적을 계산하는 함수."""
        return v1[0] * v2[1] - v1[1] * v2[0]

    def is_same_direction(v1, v2):
        """두 벡터의 외적의 부호가 같은지 확인."""
        return vector_cross_product(v1, v2) >= 0

    # 사각형의 네 꼭짓점과 점을 연결하는 벡터를 계산
    for i in range(4):
        v1 = (rectangle[(i + 1) % 4][0] - rectangle[i][0], rectangle[(i + 1) % 4][1] - rectangle[i][1])
        v2 = (point[0] - rectangle[i][0], point[1] - rectangle[i][1])

        # 외적이 모두 같은 부호라면 점이 사각형 내부에 있음
        if not is_same_direction(v1, v2):
            return False

    return True


# Function to detect objects and track using DeepSORT and YOLO
# Function to detect objects and track using DeepSORT and YOLO
def detect_objects_with_spaces(video_source, model_path, parking_file, walking_file, device):

    # 카메라 초기화 (Jetson Orin 전용 GStreamer 파이프라인)
    if platform.system() == "Linux":
        cap = cv2.VideoCapture(video_source, cv2.CAP_V4L2)
        if not cap.isOpened():
            print("Failed to open camera with GStreamer pipeline.")
            print(" Check device index using: ls /dev/video*")
            return
    else:
        cap = cv2.VideoCapture(video_source)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 560)

    # 모델 로드 (YOLOv8)
    model = YOLO(model_path)

    # DeepSORT 초기화
    tracker = DeepSort(max_age=70, n_init=5, max_iou_distance=1, nn_budget=150)

    # JSON 파일에서 주차/이동 공간 정보 로드
    parking_data = load_json(parking_file)
    walking_data = load_json(walking_file)

    print("Tracking start... Press 'q' to exit window.")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Cam Error — Frame capture failed.")
            break

        # YOLO 추론 (CUDA 사용)
        results = model(frame, device=device)
        detections = results[0]
        dets = []

        # 탐지된 객체 처리
        if detections.boxes is not None:
            for data in detections.boxes.data.tolist():
                conf = float(data[4])
                if conf < 0.1:
                    continue
                xmin, ymin, xmax, ymax = int(data[0]), int(data[1]), int(data[2]), int(data[3])
                label = int(data[5])
                dets.append([[xmin, ymin, xmax - xmin, ymax - ymin], conf, label])

        # DeepSORT 추적기 업데이트
        tracks = tracker.update_tracks(dets, frame=frame)

        # 프레임 복제 (디스플레이용)
        frame_with_spaces = frame.copy()
        frame_with_spaces = draw_spaces(frame_with_spaces, parking_data, walking_data)

        # 트래킹된 객체 반복
        for track in tracks:
            if not track.is_confirmed():
                continue
            track_id = track.track_id
            ltrb = track.to_ltrb()
            xmin, ymin, xmax, ymax = map(int, ltrb)

            # 중심 좌표 계산
            midpoint = ((xmin + xmax) // 2, (ymin + ymax) // 2)
            space_name = check_point_in_space(midpoint, parking_data, walking_data, buffer=1)

            # 박스 및 텍스트 표시
            cv2.rectangle(frame_with_spaces, (xmin, ymin), (xmax, ymax), GREEN, 2)
            cv2.rectangle(frame_with_spaces, (xmin, ymin - 20), (xmin + 20, ymin), GREEN, -1)
            cv2.putText(frame_with_spaces, str(track_id),
                        (xmin + 5, ymin - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 2)
            cv2.circle(frame_with_spaces, midpoint, 5, GREEN, -1)

            if space_name:
                cv2.putText(frame_with_spaces, f"In {space_name}",
                            (midpoint[0], midpoint[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, YELLOW, 2)
                print(f"Track ID {track_id} is in {space_name}")

        # 결과 화면 표시
        cv2.imshow('Parking and Walking Spaces with Tracking', frame_with_spaces)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Exiting tracking window.")
            break

    # 리소스 해제
    cap.release()
    cv2.destroyAllWindows()