# YOLO 모델의 예측 스코어(신뢰도)를 확인하는 스크립트
# 트래킹 없이 순수하게 detection만 수행하여 각 객체의 신뢰도 점수를 출력

import cv2
from ultralytics import YOLO
import platform
import torch

def check_prediction_scores(model_path, video_source=0, frame_width=1920, frame_height=1080, conf_threshold=0.0):
    """
    YOLO 모델의 예측 스코어를 확인하는 함수

    Args:
        model_path: YOLO 모델 파일 경로
        video_source: 비디오 소스 (0: 웹캠, 또는 비디오 파일 경로)
        frame_width: 프레임 너비
        frame_height: 프레임 높이
        conf_threshold: 신뢰도 임계값 (이 값 이상만 표시)
    """

    # 모델 로드
    model = YOLO(model_path)

    # 디바이스 설정
    if platform.system() == "Darwin":
        device = torch.device("mps") if torch.backends.mps.is_available() else "cpu"
        cap = cv2.VideoCapture(video_source)
    elif platform.system() == "Windows":
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"
        cap = cv2.VideoCapture(video_source)
    else:  # Linux (Jetson)
        device = torch.device("cuda") if torch.cuda.is_available() else "cpu"
        cap = cv2.VideoCapture(video_source, cv2.CAP_V4L2)

    print(f"사용 디바이스: {device}")

    # 카메라 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    cap.set(cv2.CAP_PROP_FPS, 30)

    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("프레임을 읽을 수 없습니다.")
                break

            frame_count += 1

            # YOLO 예측 수행 (트래킹 없이 detection만)
            results = model.predict(frame, device=device, conf=conf_threshold, verbose=False)
            result = results[0]

            # 예측 결과가 있는 경우
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.xyxy.cpu().numpy()  # 바운딩 박스 좌표
                confidences = result.boxes.conf.cpu().numpy()  # 신뢰도 점수
                classes = result.boxes.cls.cpu().numpy()  # 클래스 ID

                print(f"\n===== Frame {frame_count} =====")
                print(f"검출된 객체 수: {len(boxes)}")

                # 각 객체의 정보 출력
                for idx, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
                    xmin, ymin, xmax, ymax = box
                    print(f"  객체 {idx + 1}:")
                    print(f"    클래스 ID: {int(cls)}")
                    print(f"    신뢰도: {conf:.4f} ({conf * 100:.2f}%)")
                    print(f"    위치: ({int(xmin)}, {int(ymin)}) - ({int(xmax)}, {int(ymax)})")

                    # 프레임에 바운딩 박스와 신뢰도 표시
                    cv2.rectangle(frame, (int(xmin), int(ymin)), (int(xmax), int(ymax)), (0, 255, 0), 2)
                    label = f"ID:{int(cls)} {conf:.3f}"
                    cv2.putText(frame, label, (int(xmin), int(ymin) - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 평균 신뢰도 계산
                avg_conf = confidences.mean()
                print(f"  평균 신뢰도: {avg_conf:.4f} ({avg_conf * 100:.2f}%)")
                print(f"  최고 신뢰도: {confidences.max():.4f} ({confidences.max() * 100:.2f}%)")
                print(f"  최저 신뢰도: {confidences.min():.4f} ({confidences.min() * 100:.2f}%)")

            # 프레임 표시
            cv2.namedWindow("Prediction Scores", cv2.WINDOW_NORMAL)
            cv2.imshow("Prediction Scores", frame)

            # 'q' 키를 누르면 종료
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n프로그램 종료")
                break

    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    # 플랫폼별 설정
    if platform.system() == "Darwin":
        MODEL_PATH = "/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/model/v3_best_medium.pt"
        VIDEO_SOURCE = 0
        FRAME_WIDTH = 1080
        FRAME_HEIGHT = 560
    elif platform.system() == "Windows":
        MODEL_PATH = "/workspace/best.pt"
        VIDEO_SOURCE = 0
        FRAME_WIDTH = 1920
        FRAME_HEIGHT = 1080
    else:  # Linux (Jetson)
        MODEL_PATH = "/workspace/ShortestPath/model/best.pt"
        VIDEO_SOURCE = 0
        FRAME_WIDTH = 1920
        FRAME_HEIGHT = 1080

    # 신뢰도 임계값 설정 (0.25 이상만 표시)
    CONF_THRESHOLD = 0.25

    print("=" * 50)
    print("YOLO 모델 예측 스코어 확인 프로그램")
    print("=" * 50)
    print(f"모델 경로: {MODEL_PATH}")
    print(f"신뢰도 임계값: {CONF_THRESHOLD}")
    print("종료하려면 'q' 키를 누르세요.")
    print("=" * 50)

    check_prediction_scores(MODEL_PATH, VIDEO_SOURCE, FRAME_WIDTH, FRAME_HEIGHT, CONF_THRESHOLD)
