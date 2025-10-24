from ultralytics import YOLO
import cv2
import platform

GREEN = (0, 255, 0)
WHITE = (255, 255, 255)

# model_path: YOLO 모델 경로 (기본 모델 사용)
def detect_objects(video_source=0,
                   model_path='/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/model/v3_best_medium.pt'):

    model = YOLO(model_path)
    if platform.system() == "linux":
        cap = cv2.VideoCapture(video_source, cv2.CAP_V4L2)
    elif platform.system() == "Darwin":
        cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Cam Error")
            break

        # YOLOv8로 객체 탐지 및 ByteTracker 추적 (persist=True로 추적 활성화)
        results = model.track(frame, persist=True, tracker="/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/custom_bytetrack.yaml", conf=0.3)

        # 추적 결과가 있는 경우 처리
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()  # 바운딩 박스 좌표
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)  # 추적 ID
            confidences = results[0].boxes.conf.cpu().numpy()  # 신뢰도
            classes = results[0].boxes.cls.cpu().numpy().astype(int)  # 클래스

            for box, track_id, conf, cls in zip(boxes, track_ids, confidences, classes):
                xmin, ymin, xmax, ymax = map(int, box)

                # 바운딩 박스 및 ID 표시
                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), GREEN, 2)
                cv2.rectangle(frame, (xmin, ymin - 20), (xmin + 20, ymin), GREEN, -1)
                cv2.putText(frame, str(track_id), (xmin + 5, ymin - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 2)

                print(f"ID: {track_id}, Class: {cls}, Conf: {conf:.2f}, Box: [{xmin}, {ymin}, {xmax}, {ymax}]")

        cv2.imshow('Tracking', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    video_source = 0
    if platform.system() == 'Darwin':
        model_path = '/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/model/v3_best_medium.pt'
    elif platform.system() == 'Linux':
        model_path = '/workspace/best.pt'

    detect_objects(video_source, model_path)
