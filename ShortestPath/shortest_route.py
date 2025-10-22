# 차량의 트래킹 정보를 받아 각 구역을 설정하고 경로를 계산하는 모듈

from __future__ import annotations
import heapq
import math
import time
import json
import copy
from types import MappingProxyType
from typing import Optional, Tuple, List, Dict, Mapping, overload
from queue import Queue
from enum import Enum
from abc import ABC

# TODO 입차 및 출차 코드 수정 필요
# TODO 

### Enum 정의 ###

class CarStatus(Enum):
    """차량 상태 Enum"""
    PARKING = "parking"
    ENTRY = "entry"
    EXIT = "exit"

    def is_parking(self) -> bool:
        """주차 중인지 확인"""
        return self == CarStatus.PARKING

    def is_entry(self) -> bool:
        """입차 중인지 확인"""
        return self == CarStatus.ENTRY

    def is_exit(self) -> bool:
        """출차 중인지 확인"""
        return self == CarStatus.EXIT

class ParkingSpaceEnum(Enum):
    """주차 구역 상태 Enum"""
    EMPTY = "empty"
    TARGET = "target"
    OCCUPIED = "occupied"
    
    def is_empty(self) -> bool:
        return self == ParkingSpaceEnum.EMPTY
    
    def is_target(self) -> bool:
        return self == ParkingSpaceEnum.TARGET
    
    def is_occupied(self) -> bool:
        return self == ParkingSpaceEnum.OCCUPIED
    

### 클래스 정의 ###

class Car:
    """
    차량 클래스

    init, entry 함수 내부에서 객체 생성
    
    """

    def __init__(
        self,
        car_id: int,
        car_number: str,
        status: CarStatus,
        entry_time: float,
        position: Tuple[float, float],
        target_parking_space_id: Optional[int] = None,
        space_id: Optional[int] = None
    ) -> None:
        """
        차량 초기화

        Args:
            car_id (int): 차량 ID
            car_number (str): 차량 번호
            status (str): 차량 상태 (entry, parking, exit, Parking)
            entry_time (float): 입차 시간
            position (Tuple[int, int]): 차량 위치 (카메라 좌표)
            target_parking_space_id (Optional[int]): 주차할 구역 ID
            route (Optional[List[int]]): 경로
            space_id (Optional[int]): 마지막 방문 구역
        """
        self.car_id: int = car_id
        self.car_number: str = car_number
        self.status: CarStatus = status
        self.entry_time: float = entry_time
        self.parking_time: Optional[float] = None
        self.position: Tuple[float, float] = position  # 카메라 좌표
        self.target_parking_space_id: Optional[int] = target_parking_space_id
        self.space_id: Optional[int] = space_id
        self.route: List[int] = []
    
    @classmethod
    def create_entry_car(cls, car_id: int, car_number: str, position: Tuple[float, float]):
        """
        차량이 입차할 때 차량을 생성 (모든 Car의 생성은 해당 메소드만을 이용)
        """

        return cls(
            car_id=car_id,
            car_number=car_number,
            status=CarStatus.ENTRY,
            entry_time=time.time(),
            position=position,
            target_parking_space_id=None,
            space_id=None
            )
    
    def delete_car(self):
        """차량이 출차할 때, 구역을 벗어났을 때 삭제"""
        
        if self.space_id is not None:
            
            if self.status == CarStatus.PARKING:
                parking_space_instances[self.space_id].remove_car(self.car_id)
            
            else:
                moving_space_instances[self.space_id].remove_car(self.car_id)
        
        self.clear_route()

    def update_in_parking(self, parking_space: ParkingSpace) -> None:
        """차량이 주차 구역에 있을 경우 실행하는 함수"""

        # 주차 구역에서 주차 구역으로 들어온 경우
        if self.status == CarStatus.PARKING:

            # 동일한 주차 구역에서 들어온 경우 로직을 수행하지 않음
            if self.space_id == parking_space.space_id:
                return

            # 다른 주차 구역에서 들어온 경우 기존의 주차 구역에서 차량 삭제
            elif self.space_id is not None:
                parking_space_instances[self.space_id].remove_car(self.car_id)

        # 이동 구역에서 주차 구역으로 들어온 경우
        else:
            
            # 다른 이동 구역에서 들어온 경우 기존의 이동 구역에서 차량 삭제
            if self.space_id is not None:
                moving_space_instances[self.space_id].remove_car(self.car_id)
            
            if self.target_parking_space_id is not None:
                parking_space_instances[self.target_parking_space_id].set_empty()
                

        parking_space.append_car(self.car_id)
        self.set_parking(parking_space)

    def update_in_moving(self, moving_space: MovingSpace) -> None:
        """차량이 이동 구역에 있을 경우 실행하는 함수"""
        
        # 주차 구역에서 이동 구역으로 들어온 경우
        if self.status == CarStatus.PARKING:

            if self.space_id is not None:
                parking_space_instances[self.space_id].remove_car(self.car_id)
                parking_space_instances[self.space_id].set_empty()

        # 이동 구역에서 이동 구역으로 들어온 경우
        else:

            # 동일한 구역일 경우 로직을 수행하지 않음
            if self.space_id == moving_space.space_id:
                return
            
            elif self.space_id is not None:
                moving_space_instances[self.space_id].remove_car(self.car_id)
        
        self.set_moving(moving_space)
        
        # 루트에 있던 구역으로 간 경우
        if moving_space.space_id in self.route:
            moving_space.append_car(self.car_id)
            self.pop_route(moving_space.space_id)
        
        # 루트에 없는 구역으로 간 경우 재계산
        else:
            moving_space.append_car(self.car_id)
            self.cal_route()


    def set_parking(self, parking_space: ParkingSpace):
        """차량이 이동 구역에서 주차 구역 또는 주차 구역에서 다른 주차 구역으로 들어왔을 때 실행되는 함수"""

        self.parking_time = time.time()
        self.space_id = parking_space.space_id
        self.status = CarStatus.PARKING
        self.clear_route()

    def set_moving(self, moving_space: MovingSpace):
        """차량이 주차 구역에서 이동 구역 또는 이동 구역에서 다른 이동 구역으로 들어왔을 때 실행되는 함수"""

        self.space_id = moving_space.space_id
        self.status = CarStatus.EXIT if self.status == CarStatus.PARKING else self.status

    def update_position(self, position: Tuple[float, float]) -> None:
        """차량 위치 업데이트"""
        self.position = position

    def update_status(self, status: CarStatus) -> None:
        """차량 상태 업데이트"""
        self.status = status

    def cal_route(self):
        """
        기존의 경로를 초기화하고 경로를 재계산하여 설정

        목표로 하는 주차 구역 또한 이곳에서 설정
        """
        self.clear_route()
        print(f"아이디: {self.car_id}, 타겟: {self.target_parking_space_id}, 구역: {self.space_id} 재계산")

        if self.space_id is not None:

            target_parking_space_id = get_target_parking_space_id(self.position, self.status)
            target_moving_space_id = get_moving_space_id_by_parking_space_id(target_parking_space_id)

            route = dijkstra(self.space_id, target_moving_space_id)

            # 출구를 향하는 경우
            if target_moving_space_id == 1:
                self.set_route(route)
                return

            # 주차 구역을 향하는 경우
            moving_space_id, parking_space_id = check_route(route)

            # 최적 경로 갱신
            if moving_space_id is not None and parking_space_id is not None:
                route = route[:route.index(moving_space_id) + 1]
                parking_space_instances[parking_space_id].set_target(self.car_id)
                self.target_parking_space_id = parking_space_id
            
            else:
                parking_space_instances[target_parking_space_id].set_target(self.car_id)
                self.target_parking_space_id = target_parking_space_id

            self.set_route(route)


    def set_route(self, route: List[int]) -> None:
        """경로 설정"""
        
        # 경로로 설정 된 구역의 혼잡도를 올림
        for space_id in route:
            moving_space_instances[space_id].append_route(self.car_id)

        self.route = route

    def clear_route(self) -> None:
        """경로 초기화"""

        if len(self.route) > 0:
            # 루트가 비어있지 않을 경우 기존 루트의 혼잡도를 제거
            for space_id in self.route:
                moving_space_instances[space_id].remove_route(self.car_id)

        if self.target_parking_space_id is not None:
            parking_space_instances[self.target_parking_space_id].set_empty()

        self.route = []
        self.target_parking_space_id = None
    
    def pop_route(self, space_id: int) -> None:
        """
        루트에 따라 이동할 경우 지나온 루트 제거 하는 함수

        Args:
            space_id: 현재 위치한 구역의 ID

        Returns:
            List[int]: 삭제된 구역 ID 리스트 (혼잡도 감소 처리를 위해)
        """

        if space_id not in self.route:
            return

        i = self.route.index(space_id)
        removed_spaces = self.route[:i]
        self.route = self.route[i:]

        for removed_space in removed_spaces:
            moving_space_instances[removed_space].remove_route(self.car_id)

    def is_moving(self) -> bool:
        
        return self.status != CarStatus.PARKING and self.space_id != None
    
    def is_parking(self) -> bool:
        
        return self.status == CarStatus.PARKING and self.space_id != None

    def to_dict(self) -> Dict[str, any]:
        """딕셔너리 형태로 변환"""
        return {
            "car_id": self.car_id,
            "car_number": self.car_number,
            "status": self.status.value,  # Enum을 문자열로 변환
            "entry_time": self.entry_time,
            "parking_time": self.parking_time,
            "position": self.position,  # 카메라 좌표
            "target_parking_space_id": self.target_parking_space_id,
            "route": self.route,
            "space_id": self.space_id
        }

class Space(ABC):
    """구역 클래스"""

    def __init__(
            self,
            space_id: int,
            name: str,
            position: List[Tuple[int, int]],
    ) -> None:
        self.space_id: int = space_id
        self.name: str = name
        self.position: List[Tuple[int, int]] = position # [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] 구역의 꼭짓점 (좌상단, 우상단, 우하단, 좌하단 순서)
        self.car_set: set[int] = set()
        self.center_position: Tuple[float, float] = self.get_center_position()
    
    def is_car_in_space(self, x: float, y: float) -> bool:
        """
        특정 좌표가 (x, y) 구역의 내부에 있는지 확인하는 메소드 (Ray Casting Algorithm)

        Ray Casting: 점에서 오른쪽으로 수평선을 그어 다각형 경계와 교차하는 횟수를 센다.
        - 홀수번 교차: 내부
        - 짝수번 교차: 외부

        성능: O(n) - 사각형의 경우 n=4

        Args:
            x: 확인할 x 좌표
            y: 확인할 y 좌표
        Return:
            bool 해당 점이 구역 안에 있는지 여부
        """
        rectangle = self.position
        n = len(rectangle)

        # 점이 다각형의 경계에 있는지 확인
        for i in range(n):
            p1 = rectangle[i]
            p2 = rectangle[(i + 1) % n]
            # 동일 선상 여부 및 선분 내 존재 여부 확인
            cross_product = (y - p1[1]) * (p2[0] - p1[0]) - (x - p1[0]) * (p2[1] - p1[1])
            if abs(cross_product) < 1e-9:  # 부동 소수점 비교를 위한 허용 오차 사용
                if min(p1[0], p2[0]) <= x <= max(p1[0], p2[0]) and \
                   min(p1[1], p2[1]) <= y <= max(p1[1], p2[1]):
                    return True

        # 경계에 없으면 Ray Casting 알고리즘 사용
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = rectangle[i]
            xj, yj = rectangle[j]

            # 해당 변이 점에서 우측으로 쏜 수평선과 교차하는지 확인
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside

            j = i

        return inside
    
    def append_car(self, car_id: int):
        """
        구역에 차량이 들어온 경우 처리
        """
        self.car_set.add(car_id)

    def remove_car(self, car_id: int):
        """
        구역에서 차량이 나간 경우 처리
        """
        self.car_set.remove(car_id)

    def get_center_position(self) -> Tuple[float, float]:
        """
        구역의 중앙 좌표를 반환하는 메소드

        Returns:
            Tuple[float, float]: (x, y) 중앙 좌표
        """
        # 모든 꼭짓점의 x, y 좌표 평균 계산
        x_sum = sum(point[0] for point in self.position)
        y_sum = sum(point[1] for point in self.position)
        n = len(self.position)

        return (x_sum / n, y_sum / n)


class ParkingSpace(Space):
    """주차 구역 클래스"""

    def __init__(
        self,
        space_id: int,
        name: str,
        position: List[Tuple[int, int]],
        near_moving_space_id: int,
    ) -> None:
        """
        주차 구역 초기화

        Args:
            space_id (int): 주차 구역 ID
            name (str): 주차 구역 이름
            position (List[Tuple[int, int]]): 주차 구역 좌표 [좌상단, 우상단, 우하단, 좌하단]
            status (ParkingSpaceEnum): 주차 구역 상태 (empty, occupied, target)
            car_id (Optional[int]): 차량 ID
            parking_time (Optional[float]): 주차 시간
            car_dict (Optional[Dict[int, Car]]): 차량 딕셔너리
        """
        super().__init__(space_id, name, position)
        self.near_moving_space_id: int = near_moving_space_id
        self.status: ParkingSpaceEnum = ParkingSpaceEnum.EMPTY
        self.car_id: Optional[int] = None
        self.car_number: Optional[str] = None  # 주차 또는 타겟을 하고 있는 차량 번호
        self.parking_time: Optional[float] = None

    def append_car(self, car_id: int):
        """
        주차구역에 차량이 들어온 경우 처리
        """
        if car_id in self.car_set:
            return
        
        super().append_car(car_id)

        # 구역에 처음 주차한 차량인 경우
        if len(self.car_set) == 1:

            # 원래 들어올 예정이었던 차량이 들어온 경우
            if self.status == ParkingSpaceEnum.TARGET and self.car_id == car_id:
                self.set_occupied(car_id)
            
            # 원래 들어올 예정이 아니었던 차량이 들어온 경우
            elif self.status == ParkingSpaceEnum.TARGET and self.car_id != car_id and self.car_id is not None :
                prev_car_instance = car_number_instances[self.car_id]
                self.set_occupied(car_id)
                prev_car_instance.cal_route()

            # 비어 있는 구역에 차량이 들어온 경우
            else:
                self.set_occupied(car_id)

    def remove_car(self, car_id: int):
        """
        주차구역에서 차량이 나간 경우 처리
        """
        if car_id not in self.car_set:
            return
        
        super().remove_car(car_id)

        # 구역이 비었는지 확인
        if len(self.car_set) == 0:
            self.set_empty()
        
        # 구역이 비어있지 않으나, 기존에 먼저 주차 했던 차량이 나간 경우
        elif self.car_id == car_id:
            self.set_occupied(self.car_set.pop())

    def available_target(self) -> bool:
        """주차 구역이 타겟으로 지정 가능 한 상태인지 확인하는 함수"""

        return self.status.is_empty()
    
    def set_empty(self):
        """주차 구역을 empty로 설정하는 함수"""

        if len(self.car_set) == 0:
            self.parking_time = None
            self.car_id = None
            self.car_number = None
            self.status = ParkingSpaceEnum.EMPTY
        
        else:
            car_id = self.car_set.copy().pop()
            car = car_number_instances[car_id]
            self.parking_time = car.parking_time
            self.car_id = car_id
            self.car_number = car.car_number
            self.status = ParkingSpaceEnum.OCCUPIED

    def set_target(self, car_id: int):
        """주차 구역을 target으로 설정하는 함수"""

        self.parking_time = None
        self.car_id = car_id
        self.car_number = car_number_instances[car_id].car_number
        self.status = ParkingSpaceEnum.TARGET

    def set_occupied(self, car_id):
        """주차 구역을 occupied로 설정하는 함수"""

        self.parking_time = time.time()
        self.car_id = car_id
        self.car_number = car_number_instances[car_id].car_number
        self.status = ParkingSpaceEnum.OCCUPIED

    def get_near_moving_space_id(self) -> int:
        return self.near_moving_space_id

    def to_dict(self) -> Dict[str, any]:
        """딕셔너리 형태로 변환"""
        return {
            "space_id": self.space_id,
            "name": self.name,
            "position": self.position,
            "near_moving_space_id": self.near_moving_space_id,
            "status": self.status.value,  # Enum을 문자열로 변환
            "car_id": self.car_id,
            "car_number": self.car_number,
            "parking_time": self.parking_time,
            "car_set": list(self.car_set)  # set을 list로 변환
        }

class MovingSpace(Space):
    """이동 구역 클래스"""
    
    BASE_CONGESTION: int = 100
    CAR_CONGESTION: int = 100
    ROUTE_CONGESTION: int = 100

    def __init__(
        self,
        space_id: int,
        name: str,
        position: List[Tuple[int, int]],
        congestion: int,
        near_parking_space_id: List[int],
        near_moving_space_id: List[int],
    ) -> None:
        """
        이동 구역 초기화

        Args:
            space_id (int): 이동 구역 ID
            name (str): 이동 구역 이름
            position (List[Tuple[int, int]]): 이동 구역 좌표 [좌상단, 우상단, 우하단, 좌하단]
            status (str): 주차 구역 상태 (empty, occupied, target)
            car_id (Optional[int]): 차량 ID
            entry_time (Optional[float]): 입차 시간
            parking_time (Optional[float]): 주차 시간
            car_dict (Optional[Dict[int, Car]]): 차량 딕셔너리
        """
        super().__init__(space_id, name, position)
        self.near_parking_space_id: set[int] = set(near_parking_space_id)
        self.near_moving_space_id: set[int] = set(near_moving_space_id)
        self.congestion: int = congestion
        self.route_set: set[int] = set()    # 해당 구역을 루트로 지정한 차량의 id를 저장

    def append_car(self, car_id: int):
        if car_id in self.car_set:
            return

        super().append_car(car_id)
        self.congestion += MovingSpace.CAR_CONGESTION
    
    def remove_car(self, car_id: int):
        if car_id not in self.car_set:
            return

        super().remove_car(car_id)

        self.congestion -= MovingSpace.CAR_CONGESTION

        # if len(self.car_set) == 0:
            

    def append_route(self, car_id: int):
        """루트로 해당 구역이 지정 되었을 때 실행되는 함수"""

        if car_id in self.route_set:
            return
        
        self.route_set.add(car_id)
        self.congestion += MovingSpace.ROUTE_CONGESTION
    
    def remove_route(self, car_id: int):
        """해당 구역을 지정 했던 루트가 삭제될 때 실행되는 함수"""

        if car_id not in self.route_set:
            return

        self.route_set.remove(car_id)
        self.congestion -= MovingSpace.ROUTE_CONGESTION

    def to_dict(self) -> Dict[str, any]:
        """딕셔너리 형태로 변환"""
        return {
            "space_id": self.space_id,
            "name": self.name,
            "position": self.position,
            "near_parking_space_id": list(self.near_parking_space_id),  # set을 list로 변환
            "near_moving_space_id": list(self.near_moving_space_id),  # set을 list로 변환
            "congestion": self.congestion,
            "car_set": list(self.car_set),  # set을 list로 변환
            "route_set": list(self.route_set)  # set을 list로 변환
        }


### 전역 변수 선언 ###

# 주차 구역 인스턴스를 관리하는 딕셔너리
parking_space_instances: Dict[int, ParkingSpace] = {}

# 이동 구역 인스턴스를 관리하는 딕셔너리
moving_space_instances: Dict[int, MovingSpace] = {}

# 추적하는 차량의 인스턴스를 관리하는 딕셔너리
car_number_instances: dict[int, Car] = {}

### 함수 선언 ###

# 쓰레드에서 실행 되는 메인 함수
def main(yolo_data_queue: Queue[dict[int, tuple[float, float]]], car_number_data_queue, route_data_queue, event, parking_space_path, moving_space_path, id_match_car_number_queue, car_number_response_queue, exit_queue):
    """
    쓰레드에서 호출 되어 실행되는 메인 함수로 각각의 함수를 순서대로 실행

    Args:
        yolo_data_queue (Queue): yolo로 추적한 데이터를 받기 위한 큐
        car_number_data_queue (Queue): uart로 수신 받은 차량 번호 데이터 큐
        route_data_queue (Queue): send_to_server로 데이터를 전달하기 위한 큐
        event (Event): 정지 시킨 yolo 함수를 실행 시키기 위한 이벤트 객체
        parking_space_path (str): 주차 구역 데이터 경로
        walking_space_path (str): 이동 구역 데이터 경로
        serial_port (str): 시리얼 포트
    """

    # 사전에 입차한 차량을 확인 (최초 실행 시 카메라가 늦게 활성화 되어 비어있을 수 있으므로, 10 프레임 제거)
    for i in range(10):
        yolo_data_queue.get()

    # parking_space, walking_space 설정
    initialize_space(parking_space_path, moving_space_path)

    # 최초 실행 시 사전에 입차한 차량 번호 부여
    init(yolo_data_queue)

    # tracking 쓰레드 루프 시작
    event.set()

    # 루프 실행
    roop(yolo_data_queue, car_number_data_queue, route_data_queue, id_match_car_number_queue, car_number_response_queue, exit_queue)


def init(yolo_data_queue: Queue[dict[int, tuple[float, float]]]):
    """
    프로그램 시작 시 이미 입차된 차량에 번호 부여

    Args:
        yolo_data_queue: yolo로 추적한 차량 객체의 데이터를 받기 위한 큐
    """
    tracking_data = yolo_data_queue.get()

    print("최초 실행 데이터", tracking_data)

    # 무빙 스페이스 번호 매핑 (1번~15번 구역)
    moving_space_with_car_number = {
        1: "1001",
        2: "1002",
        3: "1003",
        4: "1004",
        5: "1005",
        6: "1006",
        7: "1007",
        8: "1008",
        9: "1009",
        10: "1010",
        11: "1011",
        12: "1012",
        13: "1013",
        14: "1014",
        15: "1015",
    }

    # 파킹 스페이스 번호 매핑 (0번~22번 구역)
    parking_space_with_car_number = {
        0: "2000",
        1: "2001",
        2: "2002",
        3: "2003",
        4: "2004",
        5: "2005",
        6: "2006",
        7: "2007",
        8: "2008",
        9: "2009",
        10: "2010",
        11: "2011",
        12: "2012",
        13: "2013",
        14: "2014",
        15: "2015",
        16: "2016",
        17: "2017",
        18: "2018",
        19: "2019",
        20: "2020",
        21: "2021",
        22: "2022",
    }

    for key, value in tracking_data.items():

        matching_parking_space_id = None
        matching_moving_space_id = None

        for parking_space_id, parking_space in parking_space_instances.items():
            if parking_space.is_car_in_space(value[0], value[1]):
                print(parking_space.name, "구역", end=", ")
                matching_parking_space_id = parking_space_id

        for moving_space_id, moving_space in moving_space_instances.items():
            if moving_space.is_car_in_space(value[0], value[1]):
                print(moving_space.name, "구역", end=", ")
                matching_moving_space_id = moving_space_id

        if matching_parking_space_id in parking_space_with_car_number:
            car_number = parking_space_with_car_number[matching_parking_space_id]
        
        elif matching_moving_space_id in moving_space_with_car_number:
            car_number = moving_space_with_car_number[matching_moving_space_id]

        else:
            car_number = input(f"id {key}번 차량 번호 (차량이 아닌 오인식 객체일 경우 'del' 입력): ")

            # del을 입력 하면 해당 차량은 제외
            if car_number == "del":
                continue

        # 차량 생성
        car_number_instances[key] = Car.create_entry_car(
            car_id=key,
            car_number=car_number,
            position=value
        )

        # 주차한 차량 우선 계산
        for _, car in car_number_instances.items():
            if (parking_space := check_position(car.position, parking_space_instances)) is not None:
                car.update_in_parking(parking_space)

def entry(car_id: int, data_queue: Queue[str], arg_position: tuple[float, float], car_number_response_queue: Queue[bool]):
    """차량이 입차할 때 번호를 받아 차량 인스턴스를 생성하는 함수"""

    # 가장 최근의 데이터만 사용
    while (data_queue.qsize() != 1):
        data_queue.get()
    car_number = data_queue.get()

    print(f"입차하는 차량이 있습니다: 입출차기에서 수신한 차량 번호: {car_number}")

    target = get_target_parking_space_id((0, 0), CarStatus.ENTRY)

    # 주차장이 만차인 경우
    if target == -1:
        car_number_response_queue.put(False)
        return

    car_number_instances[car_id] = Car.create_entry_car(
        car_id=car_id,
        car_number=car_number,
        position=arg_position
    )

    car_number_response_queue.put(True)


def car_exit(car: Car, exit_queue: Queue):
    """차량이 출차하는 함수"""
    
    exit_queue.put({car.car_id: {"car_number": car.car_number}})
    car.delete_car()
    del car_number_instances[car.car_id]


def roop(yolo_data_queue: Queue[dict[int, tuple[float, float]]], car_number_data_queue: Queue[str], route_data_queue, id_match_car_number_queue, car_number_response_queue, exit_queue):
    """차량 추적 데이터와 차량 번호 데이터를 받아와 계산하는 함수

    Args:
        yolo_data_queue (Queue): yolo로 추적한 데이터를 받기 위한 큐
        car_number_data_queue (Queue): uart로 수신 받은 차량 번호 데이터 큐
        route_data_queue (Queue): send_to_server로 데이터를 전달하기 위한 큐
    """

    while True:
        # yolo로 추적한 데이터 큐에서 가져오기
        car_tracks = yolo_data_queue.get()

        id_match_car_number_queue.put(car_number_instances)

        for car_id, position in car_tracks.items():

            # 등록된 차량 확인
            if car_id in car_number_instances:

                car = car_number_instances[car_id]  # 차량 인스턴스
                car.update_position(position)

                if len(car.route) != 0:
                    print(f"{car.car_id}번 루트: {car.route}")
                
                # 주차 구역에 있는지 확인 하고 처리
                if (parking_space := check_position(position, parking_space_instances)) is not None:
                    car.update_in_parking(parking_space)
                
                # 이동 구역에 있는지 확인 하고 처리
                elif (moving_space := check_position(position, moving_space_instances)) is not None:

                    # 차량이 출구 구역에 있는 경우
                    if moving_space.space_id == 1:
                        car_exit(car, exit_queue)
                    
                    else:
                        car.update_in_moving(moving_space)
                
                # 구역 밖 처리
                else:
                    car_number_instances[car_id].delete_car()
                    del car_number_instances[car_id]

            # 등록되지 않은 차량이 입차 구역에 있으며 입차기로부터 번호판을 받은 경우
            elif moving_space_instances[15].is_car_in_space(position[0], position[1]) and car_number_data_queue.qsize() > 0:
                entry(car_id, car_number_data_queue, position, car_number_response_queue)

        # car_number_instances에 있으나 car_tracks에 없는 차량 삭제 (추적이 끊긴 차량)
        for car_id in car_number_instances.keys():
            if car_id not in car_tracks:
                car_number_instances[car_id].delete_car()

        # 차량 데이터 전송 (cars: 차량 정보, parking: 주차 구역 정보, moving: 이동 구역 정보)
        # MappingProxyType을 사용하여 read-only view 생성 (메모리 효율적)
        route_data_queue.put({
            "cars": MappingProxyType(car_number_instances),
            "parking": MappingProxyType(parking_space_instances),
            "moving": MappingProxyType(moving_space_instances),
        })

        yolo_data_queue.task_done()  # 처리 완료 신호


def initialize_space(parking_space_path, moving_space_path):
    """최초 실행 시 구역 데이터 설정"""
    global parking_space_instances
    global moving_space_instances

    # json으로 부터 parking_space 데이터를 읽어옴
    with open(parking_space_path, "r") as f:
        parking_space = json.load(f)
        parking_space = {int(key): value for key, value in parking_space.items()}  # 문자열 키를 숫자로 변환

    # json으로 부터 moving_space 데이터를 읽어옴
    with open(moving_space_path, "r") as f:
        moving_space = json.load(f)
        moving_space = {int(key): value for key, value in moving_space.items()}  # 문자열 키를 숫자로 변환

    # ParkingSpace 클래스 인스턴스 생성
    for space_id, space_data in parking_space.items():
        parking_space_instances[space_id] = ParkingSpace(
            space_id=space_id,
            name=space_data["name"],
            position=space_data["position"],
            near_moving_space_id=space_data["near_moving_space_id"]
        )

    # MovingSpace 클래스 인스턴스 생성
    for space_id, space_data in moving_space.items():
        moving_space_instances[space_id] = MovingSpace(
            space_id=space_id,
            name=space_data["name"],
            position=space_data["position"],
            congestion=space_data["congestion"],
            near_parking_space_id=space_data["near_parking_space_id"],
            near_moving_space_id=space_data["near_moving_space_id"]
        )
        
@overload
def check_position(position, spaces: Mapping[int, ParkingSpace]) -> Optional[ParkingSpace]: ...

@overload
def check_position(position, spaces: Mapping[int, MovingSpace]) -> Optional[MovingSpace]: ...
        
def check_position(position, spaces: Mapping[int, Space]) -> Optional[Space]:
    """
    차량이 해당 구역들 내에 있는지 확인하는 함수

    return: 해당 구역내에 존재할 경우 해당 구역의 인스턴스를, 존재 하지 않을 경우 None 반환
    """

    for _, space in spaces.items():
        if space.is_car_in_space(position[0], position[1]):
            return space
    
    return None


# 다익스트라 알고리즘
def dijkstra(arg_start_id: int, arg_goal_id: int) -> list[int]:
    """경로를 계산하여 반환하는 함수"""

    pq = []
    start_space = moving_space_instances[arg_start_id]
    heapq.heappush(pq, (start_space.congestion, arg_start_id))
    came_from = {arg_start_id: 0}
    cost_so_far = {arg_start_id: 0}

    while pq:
        current_space_id: int = heapq.heappop(pq)[1]

        if current_space_id == arg_goal_id:
            break

        current_space = moving_space_instances[current_space_id]

        for next_space_id in current_space.near_moving_space_id:
            new_cost = cost_so_far[current_space_id] + moving_space_instances[next_space_id].congestion
            if next_space_id not in cost_so_far or new_cost < cost_so_far[next_space_id]:
                cost_so_far[next_space_id] = new_cost
                heapq.heappush(pq, (new_cost, next_space_id))
                came_from[next_space_id] = current_space_id

    # 경로를 역추적하여 반환
    current_space_id = arg_goal_id
    result_path = []
    while current_space_id:
        result_path.append(current_space_id)
        current_space_id = came_from[current_space_id]
    result_path.reverse()

    return result_path


def check_route(arg_route) -> tuple[Optional[int], Optional[int]]:
    """경로상에 주차할 구역이 있는지 확인하는 함수"""

    for moving_space_id in arg_route:
        for parking_space_id in moving_space_instances[moving_space_id].near_parking_space_id:
            if parking_space_id != -1 and parking_space_instances[parking_space_id].available_target():
                return moving_space_id, parking_space_id

    return None, None


def get_target_parking_space_id(position: tuple[float, float], car_status: CarStatus) -> int:
    """
    차량의 위치를 받아 가장 가까운 목표 설정 가능한 주차 공간 ID를 반환하는 함수.

    Args:
        position: 대상 차량의 위치 (x, y)

    Returns:
        int: 가장 가까운 주차 공간 ID 또는 -1 (주차 공간이 없는 경우)
    """

    # 출구를 향하는 경우 출구 구역의 번호를 반환
    if car_status == CarStatus.EXIT:
        return -1

    # 주차 공간 중 가장 가까운 빈 공간 찾기
    min_distance = float('inf')
    nearest_parking_space_id = None

    for space_id, parking_space in parking_space_instances.items():

        if parking_space.available_target():
            # 주차 구역의 중앙 좌표 가져오기
            center_x, center_y = parking_space.get_center_position()

            # 차량 위치와 주차 구역 중심 간 유클리드 거리 계산
            distance = math.sqrt((position[0] - center_x)**2 + (position[1] - center_y)**2)

            # 최소 거리 업데이트
            if distance < min_distance:
                min_distance = distance
                nearest_parking_space_id = space_id

    if nearest_parking_space_id is not None:
        return nearest_parking_space_id
    else:
        return -1


def get_moving_space_id_by_parking_space_id(parking_space_id: int) -> int:
    """
    주차 구역의 아이디로 이동 구역의 아이디를 반환하는 함수
    
    주차 구역의 아이디가 -1인 경우 출구 구역인 1을 반환
    """
    
    if parking_space_id == -1:
        return 1

    return parking_space_instances[parking_space_id].get_near_moving_space_id()
