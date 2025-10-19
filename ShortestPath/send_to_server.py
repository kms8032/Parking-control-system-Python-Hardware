# 웹서버와 아두이노로 데이터를 정제하여 전송

import socketio
import time
import queue
import json
import serial
import numpy as np
import cv2
import platform
from enum import Enum
from types import MappingProxyType
from typing import Mapping, TypeVar, Protocol
from shortest_route import Car, CarStatus, ParkingSpace, MovingSpace

# to_dict 메서드를 가진 객체를 위한 Protocol
class ToDictable(Protocol):
    def to_dict(self) -> dict: ...

T = TypeVar('T', bound=ToDictable)

class Direction(Enum):
    RIGHT = "right"
    LEFT = "left"
    UP = "up"
    DOWN = "down"


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
arduino_data = {}

# 이전에 아두이노로 전송한 데이터
previous_arduino_data = None

# 경로를 안내하는 디스플레이의 구역 번호 (아두이노의 메트릭스 순서에 맞게 조정)
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
    :param quadrilateral: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] 사각형의 네 꼭짓점 좌표 (좌상단, 우상단, 우하단, 좌하단 순서)
    :param arg_web_coordinate: 변환 대상 구역의 웹 좌표 내 직사각형 [(x1, y1), (x2, y2)] 좌상단 및 우하단 좌표
    :return: 변환된 웹 내 점의 좌표 (x, y)
    """

    # 사각형의 네 꼭짓점 좌표 배열화
    quad_pts = np.array(quadrilateral, dtype="float32")

    # 웹 좌표 내 직사각형 꼭짓점 설정
    web_top_left, web_bottom_right = arg_web_coordinate
    rect_pts = np.array([
        [web_top_left[0], web_top_left[1]],
        [web_bottom_right[0], web_top_left[1]],
        [web_bottom_right[0], web_bottom_right[1]],
        [web_top_left[0], web_bottom_right[1]]
    ], dtype="float32")

    # 투시 변환 행렬 계산
    transform_matrix = cv2.getPerspectiveTransform(quad_pts, rect_pts)

    # 특정 점을 배열로 변환하여 투시 변환 적용
    point_array = np.array([[point]], dtype="float32")  # (px, py)
    transformed_point = cv2.perspectiveTransform(point_array, transform_matrix)

    # 결과 좌표 반환
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

    # 직사각형 중심 계산
    center_x = (top_left[0] + bottom_right[0]) / 2
    center_y = (top_left[1] + bottom_right[1]) / 2

    # 상하좌우 반전
    reflected_x = 2 * center_x - px
    reflected_y = 2 * center_y - py

    return reflected_x, reflected_y


def cal_display_direction(display_center: tuple[float, float], next_center: tuple[float, float]) -> Direction:
    """
    중심점을 이용해서 다음 구역의 방향을 반환하는 함수
    """
    
    # display 구역과 다음 구역의 중심점 좌표 차이 계산
    delta_x = abs(display_center[0] - next_center[0])
    delta_y = abs(display_center[1] - next_center[1])

    if delta_x > delta_y:
        if display_center[0] < next_center[0]:
            return Direction.LEFT
        else:
            return Direction.RIGHT
    
    else:
        if display_center[1] < next_center[1]:
            return Direction.UP
        else:
            return Direction.DOWN


def cal_web_position(space_id, car_id, cars):
    transformed_x, transformed_y = transform_point_in_quadrilateral_to_rectangle(
        cars[car_id]["position"],
         walking_space[space_id]["position"],
         web_coordinates[space_id]
    )

    reflect_x, reflect_y = reflect_point_in_rectangle((transformed_x, transformed_y), web_coordinates[space_id])

    return reflect_x, reflect_y


def to_dict_mapping(objects: Mapping[int, T]) -> dict[int, dict]:
    """
    to_dict 메서드를 가진 객체들의 Mapping을 딕셔너리로 변환

    Args:
        objects: Car, ParkingSpace, MovingSpace 등 to_dict() 메서드를 가진 객체들의 Mapping

    Returns:
        각 객체를 딕셔너리로 변환한 결과
    """
    return {obj_id: obj.to_dict() for obj_id, obj in objects.items()}


# 소켓 지정
sio = socketio.Client(reconnection=True, reconnection_attempts=5, reconnection_delay=2)

# @sio.event
# def connect():
#     print("Connection established")

# @sio.event
# def disconnect():
#     print("Disconnected from server")

def send_to_server(uri, route_data_queue):
    # 서버 연결
    global arduino_data
    global previous_arduino_data
    global walking_space

    # 서버 연결
    # sio.connect(uri)

    while True:
        try:
            # Queue에서 데이터가 있을 때까지 대기
            # MappingProxyType으로 받은 read-only 데이터
            data = route_data_queue.get(timeout=1)

            # 타입 언패킹
            cars: Mapping[int, Car] = data["cars"]  # 차량 데이터
            parking_spaces: Mapping[int, ParkingSpace] = data["parking"]  # 주차 구역 데이터
            moving_spaces: Mapping[int, MovingSpace] = data["moving"]  # 이동 구역 데이터

            cars_dict = {}
            display_dict: dict[int, list[tuple[str, str]]] = { 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] }

            for car_id, car in cars.items():
                cars_dict[car_id] = car.to_dict()

                route = car.route

                if route and len(route) >= 2 and route[1] in DISPLAY_SPACE:
                    dispaly_center = moving_spaces[route[1]].center_position

                    if len(route) == 2 and car.target_parking_space_id is not None:
                        next_center = parking_spaces[car.target_parking_space_id].center_position
                    elif len(route) > 2:
                        next_center = moving_spaces[route[2]].center_position
                    else:
                        continue

                    display_number = DISPLAY_SPACE.index(route[1]) + 1
                    direction = cal_display_direction(dispaly_center, next_center)

                    display_dict[display_number].append((car.car_number, direction.value))

            # 모든 객체를 딕셔너리로 변환 (단일 함수 사용)
            send_data = {
                "time": time.time(),
                "cars": to_dict_mapping(cars),
                "parking_spaces": to_dict_mapping(parking_spaces),
                "moving_spaces": to_dict_mapping(moving_spaces),
                "display": display_dict,
            }

            print(f"Send data: {send_data}")

            # for space_id, car_ids in walking_cars.items():  # car_ids는 리스트가 됨
            #     for car_id in car_ids:
            #         # 차량 목록에 없는 경우 무시
            #         if car_id not in cars:
            #             continue

            #         # 웹페이지에 표시할 좌표 계산
            #         x, y = cal_web_position(space_id, car_id, cars)
            #         if car_id not in moving_data:
            #             moving_data[car_id] = {"car_number": cars[car_id]["car_number"],
            #                                    "status": cars[car_id]["status"],
            #                                    "entry_time": cars[car_id]["entry_time"]}
            #         moving_data[car_id]["position"] = (x, y)

            # # 서버로 데이터 전송
            # sio.emit('message', send_data)

            # # 전송 데이터를 파일로 기록
            # with open('send_data.json', 'a', encoding='utf-8') as f:
            #     json.dump(send_data, f, ensure_ascii=False, indent=2)
            #     f.write('\n' + '='*50 + '\n')  # 구분선 추가

        except queue.Empty:
            # Queue가 비었을 때는 잠시 대기
            print("Queue is empty")
            time.sleep(1)
            continue
