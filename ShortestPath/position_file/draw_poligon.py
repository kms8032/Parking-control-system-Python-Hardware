import cv2
import numpy as np
import json
import platform

# 전역 변수 초기화
zones = []
current_polygon = []
max_zones = 22
space_type = ""  # parking_space 또는 walking_space 중 하나를 선택

# 주차 구역 또는 이동 구역 데이터를 저장할 딕셔너리
parking_space = {}
walking_space = {}

# 이동 구역의 인접한 주차 구역 리스트
walking_space_near_parking = [[-1], [0, ], [1, 2, 3], [4, 5, 14], [6, 7], [8, 9, 15, 16], [], [], [17, 18], [10, 11], [12, 13, 19, 20], [], [], [21], []]

# 주차 구역의 이름 리스트 (A1, A2, ..., D9)
parking_zone_names = [
    "A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4",
    "C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4", "D5", "D6",
    "D7", "D8", "D9"
]

# 이동 구역의 이름 리스트 (Entry, Path, Exit, etc.)
walking_zone_names = [
    "Exit", "Path_2", "Path_3", "Path_4", "Path_5", "Path_6",
    "Path_7", "Path_8", "Path_9", "Path_10", "Path_11", "Path_12",
    "Path_13", "Path_14", "Entry"
]

# 마우스 콜백 함수
def draw_polygon(event, x, y, flags, param):
    global current_polygon, image_copy

    # 마우스 왼쪽 클릭 시 점 추가
    if event == cv2.EVENT_LBUTTONDOWN:
        current_polygon.append((x, y))

    # 실시간으로 선을 그리기 위해 마우스 이동 중 그리기
    if event == cv2.EVENT_MOUSEMOVE and current_polygon:
        image_copy = image.copy()  # 원본 이미지 복사
        for zone in zones:
            # 기존 다각형 그리기
            cv2.polylines(image_copy, [np.array(zone)], isClosed=True, color=(0, 255, 0), thickness=2)
        # 현재 그리는 다각형 그리기
        pts = np.array(current_polygon + [(x, y)], np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(image_copy, [pts], isClosed=False, color=(255, 0, 0), thickness=2)

# 웹캠에서 한 프레임 캡처하기
if platform.system() == 'Darwin':
    cap = cv2.VideoCapture(0)
elif platform.system() == 'Linux':
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 560)
if not cap.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

ret, frame = cap.read()
cap.release()
if not ret:
    print("이미지를 캡처할 수 없습니다.")
    exit()

image = frame.copy()
image_copy = image.copy()

# 구역 선택: 1 = parking_space, 2 = walking_space
while True:
    choice = input("Choose zone type (1: parking_space, 2: walking_space): ")
    if choice == '1':
        space_type = "parking_space"
        max_zones = 23
        zone_names = parking_zone_names
        break
    elif choice == '2':
        space_type = "walking_space"
        max_zones = 17
        zone_names = walking_zone_names
        break
    else:
        print("Invalid choice, please select 1 or 2.")

# 윈도우 설정 및 마우스 콜백 함수 등록
cv2.namedWindow('Zones')
cv2.setMouseCallback('Zones', draw_polygon)

zone_index = 0  # 구역 번호를 위한 인덱스

while True:
    cv2.imshow('Zones', image_copy)
    key = cv2.waitKey(1) & 0xFF

    # Enter 키를 누르면 현재 다각형을 확정하고 저장
    if key == 13:  # Enter 키
        if len(current_polygon) > 2:
            # 다각형 좌표 저장
            zones.append(current_polygon)

            # 구역 데이터 저장
            if space_type == "parking_space":
                parking_space[zone_index] = {
                    "name": zone_names[zone_index],
                    "status": "empty",
                    "car_id": None,
                    "position": [list(point) for point in current_polygon]
                }
            elif space_type == "walking_space":
                walking_space[zone_index + 1] = {
                    "name": zone_names[zone_index],
                    "position": [list(point) for point in current_polygon],
                    "parking_space": walking_space_near_parking[zone_index]
                }

                if zone_index == 14:
                    break

            # 다음 구역으로 이동
            zone_index += 1
            current_polygon = []
            print(f"Zone {zone_index} added.")

            # 만약 지정된 구역 수가 모두 그려지면 종료
            if zone_index >= max_zones:
                print(f"All {space_type} zones have been defined.")
                break
        else:
            print("다각형을 만들기 위해 최소 3개의 점이 필요합니다.")

    # ESC 키를 누르면 종료
    elif key == 27:  # ESC 키
        break

cv2.destroyAllWindows()

# 결과 출력 및 저장
if space_type == "parking_space":
    print("Parking space data:")
    for idx, zone in parking_space.items():
        print(f"Zone {idx}: {zone}")

    # JSON 파일로 저장
    with open('parking_space.json', 'w') as f:
        json.dump(parking_space, f, indent=4)

    print("Parking space data saved to parking_space.json.")

elif space_type == "walking_space":
    print("Walking space data:")
    for idx, zone in walking_space.items():
        print(f"Zone {idx}: {zone}")

    # JSON 파일로 저장
    with open('walking_space.json', 'w') as f:
        json.dump(walking_space, f, indent=4)

    print("Walking space data saved to walking_space.json.")
