import json
import cv2
import numpy as np

# 색상 정의
RED = (0, 0, 255)
WHITE = (255, 255, 255)
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (0, 255, 255)

# JSON 로드 함수
def load_json(filename):
    with open(filename, 'r') as file:
        return json.load(file)

# 주차/이동 구역 그리기
def draw_spaces(image, parking_data, walking_data):
    # 주차 구역
    for space in parking_data.values():
        points = np.array(space["position"], np.int32)
        cv2.polylines(image, [points], isClosed=True, color=RED, thickness=2)
        centroid = points.mean(axis=0).astype(int)
        cv2.putText(image, space["name"], (centroid[0], centroid[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

    # 이동 구역
    for space in walking_data.values():
        points = np.array(space["position"], np.int32)
        cv2.polylines(image, [points], isClosed=True, color=BLUE, thickness=2)
        centroid = points.mean(axis=0).astype(int)
        cv2.putText(image, space["name"], (centroid[0], centroid[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, BLUE, 2)
    return image

# 프레임 큐에서 시각화
def visualize_from_queue(frame_queue, parking_file, walking_file):
    """
    YOLO 추적 스레드(frame_queue)로부터 전달된 프레임을 받아 실시간으로 표시하는 함수.
    """
    parking_data = load_json(parking_file)
    walking_data = load_json(walking_file)

    print("시각화 스레드 시작 — 프레임 수신 대기 중...")

    while True:
        if frame_queue.empty():
            continue

        frame = frame_queue.get()

        # 좌표 시각화
        frame_with_spaces = draw_spaces(frame.copy(), parking_data, walking_data)

        cv2.imshow("Parking Visualization", frame_with_spaces)

        # 'q' 키로 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("시각화 종료.")
            break

    cv2.destroyAllWindows()