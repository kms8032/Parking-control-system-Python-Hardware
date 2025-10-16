# YOLOv8와 DeepSORT를 이용한 객체 추적

import queue
from deep_sort_realtime.deepsort_tracker import DeepSort
import cv2
from ultralytics import YOLO
import platform
import torch


def main(yolo_data_queue, event, model_path, video_source=0, frame_queue=None):
    model = YOLO(model_path)

    device = None

    if platform.system() == "Darwin":
        cap = cv2.VideoCapture(video_source)
        device = torch.device("mps") if torch.backends.mps.is_available() else "cpu"

    elif platform.system() == "Linux":
        cap = cv2.VideoCapture(video_source)
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

    elif platform.system() == "Windows":
        cap = cv2.VideoCapture(video_source)
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

    # 해상도 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 560)

    # DeepSORT 초기화
    tracker = DeepSort(max_age=70, n_init=1, max_iou_distance=1, nn_budget=150)

    # 사전에 주차 되어 있는 차량 데이터 전송
    for _ in range(11):
        one_frame(cap, model, tracker, yolo_data_queue, device, frame_queue)

    # 사전 주차 되어 있는 차량의 번호판 입력 기다림
    event.wait()

    while True:
        one_frame(cap, model, tracker, yolo_data_queue, device, frame_queue)


def one_frame(cap, model, tracker, yolo_data_queue, device, frame_queue=None):
    """한 프레임을 처리하는 함수"""

    ret, frame = cap.read()
    if not ret:
        print("Cam Error")
        return

    # YOLOv8로 객체 탐지 수행
    results = model(frame, device=device)

    detections = results[0]
    dets = []

    if detections.boxes is not None:
        for data in detections.boxes.data.tolist():
            conf = float(data[4])
            if conf < 0.1:
                continue

            xmin, ymin, xmax, ymax = int(data[0]), int(data[1]), int(data[2]), int(data[3])
            label = int(data[5])
            dets.append([[xmin, ymin, xmax - xmin, ymax - ymin], conf, label])

    tracks = tracker.update_tracks(dets, frame=frame)
    tracked_objects = {}

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = track.track_id
        ltrb = track.to_ltrb()
        xmin, ymin, xmax, ymax = map(int, ltrb)
        x_center = (xmin + xmax) // 2
        y_center = (ymin + ymax) // 2
        tracked_objects[track_id] = {'position': (x_center, y_center)}

        # Draw bounding box and track id on frame for visualization
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        cv2.putText(frame, f'ID: {track_id}', (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    print("yolo_tracking: ", tracked_objects)
    yolo_data_queue.put({"vehicles": tracked_objects})

    if frame_queue is not None:
        frame_queue.put(frame.copy())


if __name__ == '__main__':
    que = queue.Queue()