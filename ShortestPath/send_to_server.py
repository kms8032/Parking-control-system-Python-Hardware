import socketio
import time
import queue
import json
import numpy as np
import cv2
import platform

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

# 아두이노로 전송할 데이터
rpi_data = {}

# 이전에 전송한 데이터
previous_rpi_data = None

# 디스플레이 구역 번호
DISPLAY_SPACE = (12, 7, 2, 14, 9, 4)

# 이동 구역 좌표
walking_space = {}


# ====== 함수들 ======
def calculate_center(points):
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]
    return (sum(x_coords) / len(points), sum(y_coords) / len(points))


def transform_point_in_quadrilateral_to_rectangle(point, quadrilateral, arg_web_coordinate):
    quad_pts = np.array(quadrilateral, dtype="float32")
    web_top_left, web_bottom_right = arg_web_coordinate
    rect_pts = np.array([
        [web_top_left[0], web_top_left[1]],
        [web_bottom_right[0], web_top_left[1]],
        [web_bottom_right[0], web_bottom_right[1]],
        [web_top_left[0], web_bottom_right[1]]
    ], dtype="float32")
    transform_matrix = cv2.getPerspectiveTransform(quad_pts, rect_pts)
    transformed_point = cv2.perspectiveTransform(np.array([[point]], dtype="float32"), transform_matrix)
    return tuple(map(float, transformed_point[0][0]))


def reflect_point_in_rectangle(point, rectangle_corners):
    px, py = point
    (x1, y1), (x2, y2) = rectangle_corners
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return (2 * cx - px, 2 * cy - py)


def set_rpi_data(route, value):
    display_area = walking_space[route[1]]
    next_area = walking_space[route[2]]
    display_area_id = DISPLAY_SPACE.index(route[1]) + 1
    display_center = calculate_center(display_area["position"])
    next_center = calculate_center(next_area["position"])
    delta_x = abs(display_center[0] - next_center[0])
    delta_y = abs(display_center[1] - next_center[1])

    # 방향 계산 (기존 로직 유지)
    if delta_x > delta_y:
        if display_center[0] < next_center[0]:
            direction = "left"
        else:
            direction = "right"
    else:
        if display_center[1] < next_center[1]:
            direction = "up"
        else:
            direction = "down"

    rpi_data[display_area_id] = {
        "car_number": value.get("car_number", "No Number"),
        "direction": direction
    }


def cal_web_position(space_id, car_id, cars):
    tx, ty = transform_point_in_quadrilateral_to_rectangle(
        cars[car_id]["position"],
        walking_space[space_id]["position"],
        web_coordinates[space_id]
    )
    return reflect_point_in_rectangle((tx, ty), web_coordinates[space_id])


# ====== 소켓 설정 ======
sio = socketio.Client(reconnection=True, reconnection_attempts=5, reconnection_delay=2)


@sio.event
def connect():
    print("✅ Connected to server")


@sio.event
def disconnect():
    print("❌ Disconnected from server")


# ====== 메인 함수 ======
def send_to_server(uri, route_data_queue, parking_space_path, walking_space_path):
    global rpi_data, previous_rpi_data, walking_space

    sio.connect(uri)

    # walking_space 로드
    with open(walking_space_path, "r") as f:
        walking_space = json.load(f)
        walking_space = {int(k): v for k, v in walking_space.items()}

    while True:
        try:
            data = route_data_queue.get(timeout=1)
            print(f"send_to_server에서 받은 데이터: {data}")

            cars = data["cars"]
            parking_data = data["parking"]

            send_data = {"time": time.time()}
            moving_data = {}

            # 차량 상태(entry/exit)
            for car_id, value in cars.items():
                if value["status"] == "entry":
                    parking_data[value["parking"]]["entry_time"] = value["entry_time"]
                    moving_data[car_id] = {
                        "entry_time": value["entry_time"],
                        "car_number": value["car_number"],
                        "status": value["status"]
                    }
                elif value["status"] == "exit":
                    moving_data[car_id] = {
                        "entry_time": value["entry_time"],
                        "car_number": value["car_number"],
                        "status": value["status"]
                    }

            # 이동 차량 좌표 계산
            walking_cars = data["walking"]
            for space_id, car_ids in walking_cars.items():
                for car_id in car_ids:
                    if car_id not in cars:
                        continue
                    x, y = cal_web_position(space_id, car_id, cars)
                    if car_id not in moving_data:
                        moving_data[car_id] = {
                            "car_number": cars[car_id]["car_number"],
                            "status": cars[car_id]["status"],
                            "entry_time": cars[car_id]["entry_time"]
                        }
                    moving_data[car_id]["position"] = (x, y)

            send_data["parking"] = parking_data
            send_data["moving"] = moving_data
            print(f"Sending path: {send_data}")

            # 서버로 전송
            sio.emit('message', send_data)

            # 아두이노용 데이터 생성
            rpi_data.clear()
            processed_display_areas = set()
            for car_id, value in cars.items():
                route = value["route"]
                if route and len(route) > 2 and route[1] in DISPLAY_SPACE:
                    display_area_id = DISPLAY_SPACE.index(route[1]) + 1
                    if display_area_id not in processed_display_areas:
                        set_rpi_data(route, value)
                        processed_display_areas.add(display_area_id)

            print(f"rpi data: {rpi_data}")
            print(f"Previous data: {previous_rpi_data}")

            # 이전 데이터와 다를 때만 서버로 송신
            if rpi_data != previous_rpi_data:
                previous_rpi_data = rpi_data.copy()
                sio.emit("rpi_data", rpi_data)
                print("rpi data sent to server!")

        except queue.Empty:
            time.sleep(1)
            continue