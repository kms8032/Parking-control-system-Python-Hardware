# YOLOv8와 DeepSORT를 이용한 객체 추적

import queue
from deep_sort_realtime.deepsort_tracker import DeepSort
import cv2
from ultralytics import YOLO
import platform
import torch

def main(yolo_data_queue, frame_queue, event, model_path, video_source):

    model = YOLO(model_path)

    device = None
    if platform.system() == "Darwin":
        cap = cv2.VideoCapture(video_source)
        device = torch.device("mps") if torch.backends.mps.is_available() else "cpu"

    elif platform.system() == "Linux":
        cap = cv2.VideoCapture(video_source, cv2.CAP_V4L2)
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

    elif platform.system() == "Windows":
        cap = cv2.VideoCapture(video_source)
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 560)

    # DeepSORT 초기화
    tracker = DeepSort(max_age=70, n_init=1, max_iou_distance=1, nn_budget=150)

    # 사전에 주차 되어 있는 차량 데이터 전송
    for _ in range(11):
        one_frame(cap, model, tracker, yolo_data_queue, frame_queue, device)

    # 사전 주차 되어 있는 차량의 번호판 입력 기다림
    event.wait()

    while True:
        one_frame(cap, model, tracker, yolo_data_queue, frame_queue, device)


def one_frame(cap, model, tracker, yolo_data_queue, frame_queue, device):
    """
    한 프레임을 처리하는 함수
    """

    ret, frame = cap.read()
    if not ret:
        print("Cam Error")
        return

    # YOLOv8로 객체 탐지 수행
    results = model(frame, device=device)

    # 탐지 결과 추출
    detections = results[0]  # 단일 이미지이므로 첫 번째 결과 사용
    dets = []

    if detections.boxes is not None:
        for data in detections.boxes.data.tolist():  # Boxes 객체
            # 바운딩 박스 좌표 및 신뢰도 추출
            print(data)
            conf = float(data[4])  # 신뢰도 추출
            if conf < 0.1:
                continue

            xmin, ymin, xmax, ymax = int(data[0]), int(data[1]), int(data[2]), int(data[3])
            label = int(data[5])

            dets.append([[xmin, ymin, xmax - xmin, ymax - ymin], conf, label])

    tracks = tracker.update_tracks(dets, frame=frame)

    # 객체 정보 저장을 위한 딕셔너리
    tracked_objects = {}

    for track in tracks:

        if not track.is_confirmed():
            continue

        track_id = track.track_id
        ltrb = track.to_ltrb()

        xmin, ymin, xmax, ymax = int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])
        x_center = (xmin + xmax) // 2
        y_center = (ymin + ymax) // 2

        # 딕셔너리에 저장
        tracked_objects[track_id] = {'position': (x_center, y_center)}

    # 객체 정보를 큐에 저장
    print("yolo_tracking: ", tracked_objects)
    yolo_data_queue.put({"vehicles": tracked_objects})

    # 프레임을 메인 스레드로 전송 (GUI 표시용)
    if not frame_queue.full():
        frame_queue.put((frame, tracks))

if __name__ == '__main__':
    que = queue.Queue()