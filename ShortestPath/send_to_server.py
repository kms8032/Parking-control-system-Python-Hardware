import socketio
import time
import queue
import json
import numpy as np
import cv2

# 웹 페이지 각 구역 좌표
web_coordinates = {
        1: [(-50, 100), (0, 200)],
        2: [(0, 100), (300, 200)],
        3: [(300, 100), (650, 200)],
        4: [(650, 100), (1150, 200)],
        5: [(10, 200), (300, 430)],
        6: [(650, 200), (1150, 430)],
        7: [(0, 430), (300, 550)],
        8: [(350, 430), (650, 550)],
        9: [(650, 430), (1150, 550)],
        10: [(0, 550), (300, 780)],
        11: [(650, 550), (1150, 780)],
        12: [(0, 780), (300, 860)],
        13: [(300, 780), (650, 860)],
        14: [(650, 780), (1150, 860)],
        15: [(-50, 780), (0, 860)]
}

# 라즈베리파이로 전송할 데이터
rpi_data = {}
previous_rpi_data = None

# 경로를 안내하는 디스플레이의 구역 번호
DISPLAY_SPACE = (12, 7, 2, 14, 9, 4)

# 이동 구역의 좌표
walking_space = {}

# 사각형의 중심점 계산 함수
def calculate_center(points):
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]
    center_x = sum(x_coords) / len(points)
    center_y = sum(y_coords) / len(points)
    return (center_x, center_y)


def transform_point_in_quadrilateral_to_rectangle(point, quadrilateral, arg_web_coordinate):
    """
    사각형 내부의 특정 점을 웹 좌표 내 직사각형의 대응 위치로 변환

    :param point: (px, py) 사각형 내부의 특정 점의 좌표
    :param quadrilateral: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] 
                          사각형의 네 꼭짓점 좌표 (좌상단, 우상단, 우하단, 좌하단 순서)
    :param arg_web_coordinate: 변환 대상 구역의 웹 좌표 내 직사각형 [(x1, y1), (x2, y2)]
                               좌상단 및 우하단 좌표
    :return: 변환된 웹 내 점의 좌표 (x, y)
    """
    quad_pts = np.array(quadrilateral, dtype="float32")

    web_top_left, web_bottom_right = arg_web_coordinate
    rect_pts = np.array([
        [web_top_left[0], web_top_left[1]],
        [web_bottom_right[0], web_top_left[1]],
        [web_bottom_right[0], web_bottom_right[1]],
        [web_top_left[0], web_bottom_right[1]]
    ], dtype="float32")

    transform_matrix = cv2.getPerspectiveTransform(quad_pts, rect_pts)
    point_array = np.array([[point]], dtype="float32")  # (px, py)
    transformed_point = cv2.perspectiveTransform(point_array, transform_matrix)
    transformed_x, transformed_y = transformed_point[0][0]
    return float(transformed_x), float(transformed_y)


def reflect_point_in_rectangle(point, rectangle_corners):
    """
    직사각형의 좌상단과 우하단 좌표만을 이용해 특정 점을 상하좌우 반전시킨 좌표로 변환합니다.

    :param point: (px, py) 특정 점의 좌표
    :param rectangle_corners: [(x1, y1), (x2, y2)] 직사각형의 좌상단 및 우하단 좌표
    :return: 상하좌우 반전된 새로운 좌표 (x', y')
    """
    px, py = point
    top_left, bottom_right = rectangle_corners
    center_x = (top_left[0] + bottom_right[0]) / 2
    center_y = (top_left[1] + bottom_right[1]) / 2
    reflected_x = 2 * center_x - px
    reflected_y = 2 * center_y - py
    return reflected_x, reflected_y


# 경로에 따라 라즈베리파이에 전송할 데이터 생성
def set_rpi_data(route, value):
    display_area = walking_space[route[1]]
    next_area = walking_space[route[2]]
    display_area_id = DISPLAY_SPACE.index(route[1]) + 1

    display_center = calculate_center(display_area["position"])
    next_center = calculate_center(next_area["position"])

    delta_x = abs(display_center[0] - next_center[0])
    delta_y = abs(display_center[1] - next_center[1])

    if delta_x > delta_y:  # X 축 이동
        if display_center[0] < next_center[0]:
            rpi_data[display_area_id] = {"car_number": value.get("car_number", "No Number"), "direction": "left"}
        else:
            rpi_data[display_area_id] = {"car_number": value.get("car_number", "No Number"), "direction": "right"}
    else:  # Y 축 이동
        if display_center[1] < next_center[1]:
            rpi_data[display_area_id] = {"car_number": value.get("car_number", "No Number"), "direction": "up"}
        else:
            rpi_data[display_area_id] = {"car_number": value.get("car_number", "No Number"), "direction": "down"}


def cal_web_position(space_id, car_id, cars):
    """
    차량의 실제 위치를 웹 좌표에 매핑
    """
    transformed_x, transformed_y = transform_point_in_quadrilateral_to_rectangle(
        cars[car_id]["position"],
        walking_space[space_id]["position"],
        web_coordinates[space_id]
    )
    reflect_x, reflect_y = reflect_point_in_rectangle((transformed_x, transformed_y), web_coordinates[space_id])
    return reflect_x, reflect_y

sio = socketio.Client(reconnection=True, reconnection_attempts=5, reconnection_delay=2)

@sio.event
def connect():
    print("Connected to server")

@sio.event
def disconnect():
    print("Disconnected from server")


# ----------------- 메인 함수 -----------------
def send_to_server(uri, route_data_queue, parking_space_path, walking_space_path):
    """
    기존에는 아두이노로 시리얼 전송을 했지만,
    이제는 LAN/WebSocket을 통해 라즈베리파이 및 Express 서버로 데이터 전송
    """
    global rpi_data, previous_rpi_data, walking_space

    sio.connect(uri)

    # walking_space JSON 로드
    with open(walking_space_path, "r") as f:
        walking_space = json.load(f)
        walking_space = {int(k): v for k, v in walking_space.items()}

    while True:
        try:
            # Queue에서 데이터 수신
            data = route_data_queue.get(timeout=1)
            print(f"send_to_server 에서 받은 데이터 : {data}")

            cars = data["cars"]     # 차량 데이터
            parking_data = data["parking"]  # 주차 구역 데이터

            send_data = {"time": time.time()}
            moving_data = {}

            # 차량 상태(entry/exit) 기록
            for car_id, value in cars.items():
                if value["status"] in ("entry", "exit"):
                    moving_data[car_id] = {
                        "entry_time": value["entry_time"],
                        "car_number": value["car_number"],
                        "status": value["status"]
                    }

            # 이동 차량 위치 계산
            walking_cars = data["walking"]  # {space_id: [car_id]}
            for space_id, car_ids in walking_cars.items():
                for car_id in car_ids:
                    if car_id not in cars:
                        continue
                    x, y = cal_web_position(space_id, car_id, cars)
                    moving_data.setdefault(car_id, {
                        "car_number": cars[car_id]["car_number"],
                        "status": cars[car_id]["status"],
                        "entry_time": cars[car_id]["entry_time"]
                    })
                    moving_data[car_id]["position"] = (x, y)

            # 최종 JSON 데이터 구성
            send_data["parking"] = parking_data
            send_data["moving"] = moving_data

            print(f"Sending path: {send_data}")
            sio.emit('message', send_data)  # Express/라즈베리파이로 전송

            # 라즈베리파이 표시 데이터 생성
            rpi_data.clear()
            processed_display_areas = set()
            for car_id, value in cars.items():
                route = value["route"]
                if route and len(route) > 2 and route[1] in DISPLAY_SPACE:
                    display_area_id = DISPLAY_SPACE.index(route[1]) + 1
                    if display_area_id not in processed_display_areas:
                        set_rpi_data(route, value)
                        processed_display_areas.add(display_area_id)

            print(f"Raspberry Pi data: {rpi_data}")

        except queue.Empty:
            time.sleep(1)
            continue

if __name__ == "__main__":
    sio.connect(uri)

    rpi_data = {
        2: {"car_number": "12가3456", "direction": "right"},
        4: {"car_number": "34나7890", "direction": "down"},
        7: {"car_number": "56다1234", "direction": "left"}
    }

    while True:
        sio.emit("message", rpi_data)
        print("Data sent:", rpi_data)
        time.sleep(2)