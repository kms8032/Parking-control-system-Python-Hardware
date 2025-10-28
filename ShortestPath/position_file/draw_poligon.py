import cv2
import numpy as np
import json
import platform

# 전역 변수 초기화
zones = []
current_polygon = []
max_zones = 23
space_type = ""  # parking_space 또는 moving_space 중 하나를 선택

# 주차 구역 또는 이동 구역 데이터를 저장할 딕셔너리
parking_space = {}
moving_space = {}

# 주차 구역별 인접한 이동 구역 ID (parking_space_id -> near_moving_space_id)
parking_near_moving = {
    0: 2, 1: 3, 2: 3, 3: 3, 4: 4, 5: 4,
    6: 5, 7: 5, 8: 6, 9: 6, 10: 10, 11: 10,
    12: 11, 13: 11, 14: 4, 15: 4, 16: 6, 17: 6,
    18: 9, 19: 9, 20: 11, 21: 11, 22: 14
}

# 이동 구역별 인접한 주차 구역 및 이동 구역 리스트 (moving_space_id -> {parking, moving})
moving_connections = {
    1: {"parking": [-1], "moving": [2]},  # Exit
    2: {"parking": [0], "moving": [1, 3, 5]},  # Path_2
    3: {"parking": [1, 2, 3], "moving": [2, 4]},  # Path_3
    4: {"parking": [4, 5, 14, 15], "moving": [3, 6]},  # Path_4
    5: {"parking": [6, 7], "moving": [2, 7]},  # Path_5
    6: {"parking": [8, 9, 16, 17], "moving": [4, 9]},  # Path_6
    7: {"parking": [], "moving": [5, 8, 10]},  # Path_7
    8: {"parking": [], "moving": [7, 9]},  # Path_8
    9: {"parking": [18, 19], "moving": [6, 8, 11]},  # Path_9
    10: {"parking": [10, 11], "moving": [7, 12]},  # Path_10
    11: {"parking": [12, 13, 20, 21], "moving": [9, 14]},  # Path_11
    12: {"parking": [], "moving": [10, 13, 15]},  # Path_12
    13: {"parking": [], "moving": [12, 14]},  # Path_13
    14: {"parking": [22], "moving": [11, 13]},  # Path_14
    15: {"parking": [], "moving": [12]}  # Entry
}

# 주차 구역의 이름 리스트 (A1, A2, ..., D9)
parking_zone_names = [
    "A1", "A2", "A3", "A4", "A5", "A6",
    "B1", "B2", "B3", "B4",
    "C1", "C2", "C3", "C4",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"
]

# 이동 구역의 이름 리스트 (Exit, Path_2, ..., Entry)
moving_zone_names = [
    "Exit", "Path_2", "Path_3", "Path_4", "Path_5",
    "Path_6", "Path_7", "Path_8", "Path_9", "Path_10",
    "Path_11", "Path_12", "Path_13", "Path_14", "Entry"
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

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
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

# 구역 선택: 1 = parking_space, 2 = moving_space
while True:
    choice = input("Choose zone type (1: parking_space, 2: moving_space): ")
    if choice == '1':
        space_type = "parking_space"
        max_zones = 23  # A1~A6, B1~B4, C1~C4, D1~D9
        zone_names = parking_zone_names
        break
    elif choice == '2':
        space_type = "moving_space"
        max_zones = 15  # Exit, Path_2~14, Entry
        zone_names = moving_zone_names
        break
    else:
        print("Invalid choice, please select 1 or 2.")

# 윈도우 설정 및 마우스 콜백 함수 등록
cv2.namedWindow('Zones', cv2.WINDOW_NORMAL)
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
                    "position": [list(point) for point in current_polygon],
                    "near_moving_space_id": parking_near_moving.get(zone_index, -1)
                }
                print(f"Parking Zone {zone_index} ({zone_names[zone_index]}) added.")

            elif space_type == "moving_space":
                # moving_space는 ID가 1부터 시작
                moving_id = zone_index + 1
                connections = moving_connections.get(moving_id, {"parking": [], "moving": []})

                moving_space[moving_id] = {
                    "name": zone_names[zone_index],
                    "position": [list(point) for point in current_polygon],
                    "congestion": 100,  # 기본 혼잡도
                    "near_parking_space_id": connections["parking"],
                    "near_moving_space_id": connections["moving"]
                }
                print(f"Moving Zone {moving_id} ({zone_names[zone_index]}) added.")

            # 다음 구역으로 이동
            zone_index += 1
            current_polygon = []

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
    print("\n=== Parking Space Data ===")
    for idx, zone in parking_space.items():
        print(f"Zone {idx}: {zone['name']} -> Moving Space {zone['near_moving_space_id']}")

    # JSON 파일로 저장
    with open('parking_space.json', 'w') as f:
        json.dump(parking_space, f, indent=2)

    print("\n✅ Parking space data saved to parking_space.json.")

elif space_type == "moving_space":
    print("\n=== Moving Space Data ===")
    for idx, zone in moving_space.items():
        print(f"Zone {idx}: {zone['name']}")
        print(f"  - Near Parking: {zone['near_parking_space_id']}")
        print(f"  - Near Moving: {zone['near_moving_space_id']}")

    # JSON 파일로 저장
    with open('moving_space.json', 'w') as f:
        json.dump(moving_space, f, indent=2)

    print("\n✅ Moving space data saved to moving_space.json.")
