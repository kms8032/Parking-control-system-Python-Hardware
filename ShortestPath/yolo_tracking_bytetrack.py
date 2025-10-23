# YOLOv8의 내장 ByteTrack을 이용한 객체 추적

import queue
import cv2
from ultralytics import YOLO
import platform
import torch
from performance_profiler import profiler

def main(yolo_data_queue, frame_queue, event, model_path, video_source, frame_width, frame_height, stop_event):

    model = YOLO(model_path)

    device = None
    if platform.system() == "Darwin":
        cap = cv2.VideoCapture(video_source)
        device = torch.device("mps") if torch.backends.mps.is_available() else "cpu"

    elif platform.system() == "Windows":
        cap = cv2.VideoCapture(video_source)
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

    else:   # Linux
        cap = cv2.VideoCapture(video_source, cv2.CAP_V4L2)
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # 사전에 주차 되어 있는 차량 데이터 전송
    for _ in range(11):
        one_frame(cap, model, yolo_data_queue, frame_queue, device)

    # 사전 주차 되어 있는 차량의 번호판 입력 기다림
    event.wait()

    try:
        while not stop_event.is_set():
            one_frame(cap, model, yolo_data_queue, frame_queue, device)
    finally:
        profiler.print_stats()


def one_frame(cap, model, yolo_data_queue, frame_queue, device):
    """
    한 프레임을 처리하는 함수 (ByteTrack 사용)
    """
    ret, frame = cap.read()
    if not ret:
        print("Cam Error")
        return

    # YOLOv8 내장 ByteTrack 이용
    results = model.track(frame, device=device, persist=True, tracker="custom_bytetrack.yaml")

    # 추적 결과 추출
    result = results[0]

    # 객체 정보 저장을 위한 딕셔너리
    tracked_objects = {}

    # boxes가 있고 id가 있는 경우 (추적 성공)
    if result.boxes is not None and result.boxes.id is not None:
        boxes = result.boxes.xyxy.cpu().numpy()  # 바운딩 박스 좌표
        track_ids = result.boxes.id.cpu().numpy().astype(int)  # 추적 ID

        for box, track_id in zip(boxes, track_ids):
            xmin, ymin, xmax, ymax = box
            x_center = int((xmin + xmax) / 2)
            y_center = int((ymin + ymax) / 2)

            # 딕셔너리에 저장
            tracked_objects[int(track_id)] = (x_center, y_center)

    # 객체 정보를 큐에 저장
    yolo_data_queue.put(tracked_objects)

    # 프레임을 메인 스레드로 전송 (GUI 표시용)
    # ByteTrack 결과를 DeepSORT와 호환되는 형태로 변환
    if not frame_queue.full():
        tracks = create_track_objects(result)
        frame_queue.put((frame, tracks))

class Track:
    """DeepSORT의 Track 객체와 호환되는 간단한 클래스"""

    def __init__(self, track_id, bbox):
        self.track_id = track_id
        self._bbox = bbox  # [xmin, ymin, xmax, ymax]

    def is_confirmed(self):
        """항상 confirmed 상태로 반환"""
        return True

    def to_ltrb(self):
        """바운딩 박스를 [left, top, right, bottom] 형태로 반환"""
        return self._bbox


def create_track_objects(result):
    """
    YOLO result 객체를 Track 객체 리스트로 변환

    Args:
        result: YOLO tracking result

    Returns:
        List[Track]: Track 객체 리스트
    """
    tracks = []

    if result.boxes is not None and result.boxes.id is not None:
        boxes = result.boxes.xyxy.cpu().numpy()
        track_ids = result.boxes.id.cpu().numpy().astype(int)

        for box, track_id in zip(boxes, track_ids):
            track = Track(track_id, box)
            tracks.append(track)

    return tracks


if __name__ == '__main__':
    que = queue.Queue()
