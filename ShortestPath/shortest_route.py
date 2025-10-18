# 차량의 트래킹 정보를 받아 각 구역을 설정하고 경로를 계산하는 모듈

import heapq
import math
import time
import json
import socketio
import platform
import copy

### 변수 선언 ###

# 주차 구역의 데이터
# parking_id<int>: {
#     name<str>: 주차 구역 이름
#     status<str>: empty, occupied, target
#     car_id<int>: 차량 아이디
#     position<list>: 주차 구역의 좌표값 [좌상단, 우상단, 우하단, 좌하단]
# }
parking_space = {}

# 이동 구역의 데이터
# walking_id<int>: {
#     name<str>: 이동 구역 이름
#     parking_space<list>: 이동 구역과 연결된 주차 구역
#     position<list>: 이동 구역의 좌표값 [좌상단, 우상단, 우하단, 좌하단]
# }
walking_space = {}

# 경로를 계산할 차량
# walking_space_id<int>: car_id<int>
vehicles_to_route = {}

# 혼잡도
congestion = {
    1: {2: 1},
    2: {1: 1, 3: 1, 5: 1},
    3: {2: 1, 4: 1},
    4: {3: 1, 6: 1},
    5: {2: 1, 7: 1},
    6: {4: 1, 9: 1},
    7: {5: 1, 8: 1, 10: 1},
    8: {7: 1, 9: 1},
    9: {6: 1, 8: 1, 11: 1},
    10: {7: 1, 12: 1},
    11: {9: 1, 14: 1},
    12: {10: 1, 13: 1, 15: 1},
    13: {12: 1, 14: 1},
    14: {11: 1, 13: 1},
    15: {12: 1}
}

# 차량의 번호와 ID를 매핑 (지속적으로 추적하며 상태를 관리할 차량 목록)
# car_id<int>: {
#     status<str>: entry, parking, exit
#     parking<int>: 주차할 구역의 id
#     car_number<str>: 차량 번호
#     route<list>: 경로
#     entry_time<float>: 입차 시간
#     parking_time<float>: 주차 시간
#     last_visited_space<int>: 마지막 방문 구역
# }
car_numbers = {}

# 최초 실행 시 주차되어 있던 차량
# car_number<str>: position<list>
set_car_numbers = {}

parking_positions = {}  # 주차한 차량의 위치 정보 {구역 아이디: [차량 아이디]}

walking_positions = {}  # 이동 중인 차량의 위치 정보 {구역 아이디: [차량 아이디]}

ser = None  # 젯슨 나노에 연결된 시리얼 포트 (출차 신호 전달을 위해 사용)

sio = socketio.Client()


### 함수 선언 ###

# 쓰레드에서 실행 되는 메인 함수
def main(yolo_data_queue, car_number_data_queue, route_data_queue, event, parking_space_path, walking_space_path, serial_port, id_match_car_number_queue):
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

    # 사전에 주차 되어 있는 차량을 확인
    for i in range(10):
        yolo_data_queue.get()

    # parking_space, walking_space 설정
    initialize_data(parking_space_path, walking_space_path)

    # 최초 실행 시 주차된 차량 아이디 부여
    init(yolo_data_queue)

    # tracking 쓰레드 루프 시작
    event.set()

    # 소켓 연결
    sio.connect("http://192.168.0.10:5002")

    # 루프 실행
    roop(yolo_data_queue, car_number_data_queue, route_data_queue, serial_port, id_match_car_number_queue)


# 최초 주차된 차량 아이디 부여
def init(yolo_data_queue):
    """
    위치 정보를 이용하여 최초 실행 시 주차되어 있던 차량 아이디 부여

    Args:
        yolo_data_queue: yolo로 추적한 데이터를 받기 위한 큐
    """
    tracking_data = yolo_data_queue.get()["vehicles"]

    print("최초 실행 데이터", tracking_data)

    for key, value in tracking_data.items():
        for parking_id, parking_value in parking_space.items():
            if is_point_in_rectangle(value["position"], parking_value["position"]):
                print(parking_value["name"])

        for walking_id, walking_value in walking_space.items():
            if is_point_in_rectangle(value["position"], walking_value["position"]):
                print(walking_value["name"])

        car_number = input(f"id {key}번 차량 번호: ")
        # del을 입력 하면 해당 차량은 제외
        if car_number == "del":
            continue
        set_car_numbers[car_number] = value["position"]


def roop(yolo_data_queue, car_number_data_queue, route_data_queue, serial_port, id_match_car_number_queue):
    """차량 추적 데이터와 차량 번호 데이터를 받아와 계산하는 함수

    Args:
        yolo_data_queue (Queue): yolo로 추적한 데이터를 받기 위한 큐
        car_number_data_queue (Queue): uart로 수신 받은 차량 번호 데이터 큐
        route_data_queue (Queue): send_to_server로 데이터를 전달하기 위한 큐
        serial_port (str): 시리얼 포트
    """

    print("최초 실행 시 설정된 차량 번호", set_car_numbers)

    vehicles = yolo_data_queue.get()["vehicles"]
    first_func(vehicles)

    while True:
        # yolo로 추적한 데이터 큐에서 가져오기
        vehicles = yolo_data_queue.get()["vehicles"]

        print("최단 경로 수신 데이터", vehicles)

        id_match_car_number_queue.put(car_numbers)

        # 감지된 차량들의 위치 확인
        for vehicle_id, value in vehicles.items():
            # 차량 번호가 있는 차량 확인
            if vehicle_id in car_numbers:
                check_position(vehicle_id, value)
                car_numbers[vehicle_id]["position"] = value["position"]

            # 차량 번호가 없는 차 중 입차 구역에 있는 차량
            elif is_point_in_rectangle(value["position"], walking_space[15]["position"]):
                entry(vehicle_id, car_number_data_queue, value["position"], walking_positions)

        print("주차 구역 차량", parking_positions)
        print("이동 구역 차량", walking_positions)

        # 차량 출차 확인
        if 1 in walking_positions:
            car_exit(walking_positions, serial_port)

        # 차량 위치에 따라 주차 공간, 이동 공간, 차량 설정
        set_parking_space()
        set_walking_space(vehicles)

        # 차량이 주차 되어 있지 않으나 occupied 인 주차 구역 비움
        for space_id in parking_space:
            if parking_space[space_id]["status"] == "occupied" and space_id not in parking_positions:
                set_parking_space_car_id(space_id, None, "empty")

        print("경로를 계산할 차량", vehicles_to_route)

        # 경로 계산
        for space_id, car_id in vehicles_to_route.items():
            route = cal_route(space_id, car_id)
            car_numbers[car_id]["route"] = route

        print("car_numbers", car_numbers)
        print("parking_space", parking_space)
        print(congestion)

        # 데이터 전송 전에 parking_space에 car_number 정보 업데이트
        update_car_numbers_in_parking_space()

        print(walking_positions)

        # 차량 데이터 전송 (cars: 차량 정보, parking: 주차 구역 정보, walking: 이동 중인 차량 id)
        route_data_queue.put(copy.deepcopy({"cars": car_numbers, "parking": parking_space, "walking": walking_positions}))

        del_target()    # 트래킹이 끊긴 경우를 대비하여 이동 중인 차량이 없으면 모든 혼잡도와 목표 제거

        reset_iteration_data()  # 변수 초기화

        yolo_data_queue.task_done()  # 처리 완료 신호


def initialize_data(parking_space_path, walking_space_path):
    """최초 실행 시 구역 데이터 설정"""
    global parking_space
    global walking_space

    # json으로 부터 parking_space 데이터를 읽어옴
    with open(parking_space_path, "r") as f:
        parking_space = json.load(f)
        parking_space = {int(key): value for key, value in parking_space.items()}  # 문자열 키를 숫자로 변환

    # json으로 부터 walking_space 데이터를 읽어옴
    with open(walking_space_path, "r") as f:
        walking_space = json.load(f)
        walking_space = {int(key): value for key, value in walking_space.items()}  # 문자열 키를 숫자로 변환


def car_exit(arg_walking_positions, serial_port):
    """차량이 출차하는 함수"""
    print("출차하는 차량이 있습니다.")
    global ser

    if car_numbers[arg_walking_positions[1]]["parking"] != -1:
        parking_space[car_numbers[arg_walking_positions[1]]["parking"]]["status"] = "empty"
    del car_numbers[arg_walking_positions[1]]
    del arg_walking_positions[1]

    # Socket.IO를 통해 출차 신호 전달
    try:
        sio.emit("exit_signal", {"status": "exit"})
        print("🚗 출차 신호 전송 완료 (Socket.IO)")
    except Exception as e:
        print(f"❌ 출차 신호 전송 실패: {e}")

    print("차량이 출차했습니다.")


def entry(vehicle_id, data_queue, arg_position, arg_walking_positions):
    """차량이 입차하는 함수"""
    print("입차하는 차량이 있습니다.")
    if data_queue.qsize() > 0:
        # 가장 최근의 데이터만 사용
        while (data_queue.qsize() != 1):
            data_queue.get()
        car_number = data_queue.get()
        print(f"2번 쓰레드: 입출차기에서 수신한 차량 번호: {car_number}")
        if car_number == "[]":
            return
        car_numbers[vehicle_id] = {"car_number": car_number, "status": "entry",
                                               "route": [], "entry_time": time.time(),
                                              "position": arg_position, "last_visited_space": None}
        walking_positions[15] = vehicle_id
        # car_numbers에 차량 정보를 세팅 한 후 set_entry_target 함수를 호출하여 주차할 구역을 지정
        car_numbers[vehicle_id]["parking"] = set_target(vehicle_id)
        arg_walking_positions[15] = vehicle_id
        print("car_numbers", car_numbers)


# 경로 내의 특정 구역까지의 혼잡도를 감소시키는 함수
def decrease_congestion_target_in_route(arg_route, arg_target):
    """경로 내의 특정 구역까지의 혼잡도를 감소시키는 함수"""
    for node in arg_route:
        if node == arg_target:
            break
        for next_node in congestion[node]:
            congestion[node][next_node] -= 2


# 사전에 주차 되어 있던 차량에 번호 부여
def first_func(arg_vehicles):
    """사전에 주차 되어 있던 차량에 번호 부여"""
    print("isFirst arg_vehicles", arg_vehicles)
    print("isFirst set_car_numbers", set_car_numbers)

    for key, value in set_car_numbers.items():
        for car_id, car_value in arg_vehicles.items():
            # 오차 범위 +- 10 이내 이면 같은 차량으로 판단
            if value[0] - 10 <= car_value["position"][0] <= value[0] + 10 and \
                    value[1] - 10 <= car_value["position"][1] <= value[1] + 10:
                car_numbers[car_id] = {"car_number": key, "status": "Parking", "parking": None, "route": [], "entry_time": time.time(), "last_visited_space": None}
                print("isFirst car_numbers", car_numbers)
                break


# 경로 내의 구역의 혼잡도를 감소시키는 함수
def decrease_congestion(arg_route, arg_congestion = 2):
    """경로 내의 구역의 혼잡도를 감소시키는 함수"""
    for node in arg_route:
        for next_node in congestion[node]:
            congestion[node][next_node] -= arg_congestion


# 경로 내의 구역의 혼잡도를 증가시키는 함수
def increase_congestion(arg_route, arg_congestion = 2):
    """경로 내의 구역의 혼잡도를 증가시키는 함수"""
    for node in arg_route:
        for next_node in congestion[node]:
            congestion[node][next_node] += arg_congestion


# 주차 구역에 대한 이동 구역을 반환하는 함수
def get_walking_space_for_parking_space(arg_parking_space):
    """주차 구역에 대한 이동 구역을 반환하는 함수"""
    for key, value in walking_space.items():
        if arg_parking_space in tuple(value["parking_space"]):
            return key


# 차량의 위치를 확인하여 주차 공간 또는 이동 공간에 할당하는 함수
def check_position(vehicle_id, vehicle_value):
    """차량의 위치를 확인하여 주차 공간 또는 이동 공간에 할당하는 함수"""

    px, py = vehicle_value["position"]

    # 주차 공간 체크
    for key, value in parking_space.items():
        if str(vehicle_id) in car_numbers and is_point_in_rectangle((px, py), value["position"]):
            if key not in parking_positions:
                parking_positions[key] = []
            parking_positions[key].append(vehicle_id)
            return

    # 이동 공간 체크
    for key, value in walking_space.items():
        if str(vehicle_id) in car_numbers and is_point_in_rectangle((px, py), value["position"]):
            if key not in walking_positions:
                walking_positions[key] = []
            walking_positions[key].append(vehicle_id)
            return

    # 입차 체크
    if is_point_in_rectangle((px, py), walking_space[15]["position"]):
        if 15 not in walking_positions:
            walking_positions[15] = []
        walking_positions[15].append(vehicle_id)
        print(f"차량 {vehicle_id}은 입차 중 입니다.")
        return

    print(f"차량 {vehicle_id}의 위치를 확인할 수 없습니다.")


# 주차 공간 및 주차 차량 설정
def set_parking_space():
    """주차 공간 및 주차 차량 설정"""

    global parking_positions

    for space_id, car_list in parking_positions.items():
        for car_id in car_list:
            # 주차 중
            if parking_space[space_id]["status"] == "occupied":
                continue

            # 해당 구역에 주차 예정이 아니었던 차량이 들어온 경우
            elif parking_space[space_id]["status"] == "target" and parking_space[space_id]["car_id"] != car_id:
                # 원래 주차 예정이었던 차량 설정
                car_numbers[parking_space[space_id]["car_id"]]["parking"] = set_target(parking_space[space_id]["car_id"]) # 주차 공간 변경
                decrease_congestion(car_numbers[parking_space[space_id]["car_id"]]["route"])    # 이전 경로 혼잡도 감소
                car_numbers[parking_space[space_id]["car_id"]]["route"] = []    # 경로 초기화

                # 입차한 차량이 원래 주차 예정이었던 구역 비움
                set_parking_space_car_id(car_numbers[car_id]["parking"], None, "empty")

            # 주차 구역 설정
            set_parking_space_car_id(space_id, car_id, "occupied")

            car_numbers[car_id]["status"] = "parking"
            car_numbers[car_id]["parking"] = space_id
            decrease_congestion(car_numbers[car_id]["route"])    # 이전 경로 혼잡도 감소
            car_numbers[car_id]["route"] = []
            car_numbers[car_id]["last_visited_space"] = None


# 이동 공간 및 이동하는 차량 설정
def set_walking_space(arg_vehicles):
    """이동 공간 및 이동하는 차량 설정"""

    for space_id, car_ids in walking_positions.items():
        for car_id in car_ids:
            # 주차 한 후 최초 이동 시
            if car_numbers[car_id]["status"] == "parking":

                # 차량 설정
                if time.time() - parking_space[car_numbers[car_id]["parking"]]["parking_time"] > 5:
                    car_numbers[car_id]["status"] = "exit"
                    car_numbers[car_id]["parking"] = -1
                    car_numbers[car_id]["route"] = []
                    car_numbers[car_id]["last_visited_space"] = None

                else:
                    car_numbers[car_id]["status"] = "entry"
                    car_numbers[car_id]["route"] = []
                    car_numbers[car_id]["last_visited_space"] = None

                # 주차 구역 비우기
                set_parking_space_car_id(car_numbers[car_id]["parking"], car_id, "empty")

            # 경로에서 벗어난 경우
            if space_id not in car_numbers[car_id]["route"] and car_numbers[car_id]["route"]:
                decrease_congestion(car_numbers[car_id]["route"])    # 이전 경로 혼잡도 감소
                if car_numbers[car_id]["route"]:
                    car_numbers[car_id]["last_visited_space"] = car_numbers[car_id]["route"][0]    # 직전 방문 구역 설정
                car_numbers[car_id]["route"] = []    # 경로 초기화

                # 주차하는 차량의 경우 가까운 주차 구역으로 변경
                if car_numbers[car_id]["parking"] != -1:
                    set_parking_space_car_id(car_numbers[car_id]["parking"], car_id, "empty")  # 이전 주차 구역 비우기
                    car_numbers[car_id]["parking"] = set_target(car_id)  # 주차 구역 재설정

            elif space_id in car_numbers[car_id]["route"]:
                temp_index = car_numbers[car_id]["route"].index(space_id)

                # 경로의 첫번째 위치면 스킵
                if temp_index == 0:
                    continue

                decrease_congestion_target_in_route(car_numbers[car_id]["route"], space_id)
                car_numbers[car_id]["last_visited_space"] = car_numbers[car_id]["route"][temp_index - 1]    # 이전 방문 구역 설정
                car_numbers[car_id]["route"] = car_numbers[car_id]["route"][temp_index:]    # 경로 수정

            # 경로가 없는 경우 경로를 계산할 딕셔너리에 추가
            if not car_numbers[car_id]["route"]:
                vehicles_to_route[space_id] = car_id

            # 이동 중인 차량 위치 기록
            car_numbers[car_id]["position"] = arg_vehicles[car_id]["position"]


def cal_route(space_id, car_id):
    """
    경로를 계산하는 함수

    Args:
        space_id: 구역 아이디
        car_id: 차량 아이디

    Returns:
        list: 경로
    """
    parking_goal = get_walking_space_for_parking_space(car_numbers[car_id]["parking"])
    # if car_numbers[car_id]["last_visited_space"]:
    #     increase_congestion((car_numbers[car_id]["last_visited_space"], ), 100)  # 직전 방문 구역 혼잡도 증가
    route = a_star(congestion, space_id, parking_goal)
    # if car_numbers[car_id]["last_visited_space"]:
    #     decrease_congestion((car_numbers[car_id]["last_visited_space"], ), 100)  # 직전 방문 구역 혼잡도 감소

    # 주차를 하는 차량의 경우 경로 상에 비어 있는 주차 구역 확인
    if car_numbers[car_id]["status"] == "entry":
        amend_goal, amend_parking_space = check_route(route[:-1])
    else:
        amend_goal, amend_parking_space = None, None

    # 경로 상에 비어있는 주차 공간이 있는 경우 경로 수정 및 주차 공간 변경
    if amend_goal is not None:
        route = route[:route.index(amend_goal) + 1]
        set_parking_space_car_id(car_numbers[car_id]["parking"], car_id, "empty")   # 이전 주차 공간 비우기
        car_numbers[car_id]["parking"] = amend_parking_space  # 주차 공간 변경
        set_parking_space_car_id(amend_parking_space, car_id, "target")  # 새로운 주차 공간 설정

    increase_congestion(route)
    print(f"차량 {car_id}의 경로: {route}")
    return route


def is_point_in_rectangle(point, rectangle):
    """
    특정 좌표가 사각형 내부에 있는지 확인하는 함수.

    Args:
        point: (x, y) 확인할 좌표
        rectangle: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] 사각형의 꼭짓점 (좌상단, 우상단, 우하단, 좌하단 순서)
    Return:
        bool 해당 점이 사각형 안에 있는지 여부
    """

    def vector_cross_product(v1, v2):
        """두 벡터의 외적을 계산하는 함수."""
        return v1[0] * v2[1] - v1[1] * v2[0]

    def is_same_direction(v1, v2):
        """두 벡터의 외적의 부호가 같은지 확인."""
        return vector_cross_product(v1, v2) >= 0

    # 사각형의 네 꼭짓점과 점을 연결하는 벡터를 계산
    for i in range(4):
        v1 = (rectangle[(i + 1) % 4][0] - rectangle[i][0], rectangle[(i + 1) % 4][1] - rectangle[i][1])
        v2 = (point[0] - rectangle[i][0], point[1] - rectangle[i][1])

        # 외적이 모두 같은 부호라면 점이 사각형 내부에 있음
        if not is_same_direction(v1, v2):
            return False

    return True


# A* 알고리즘 예측 함수
def heuristic(a, b):
    # 휴리스틱 함수: 여기서는 간단하게 두 노드 간 차이만 계산 (유클리드 거리는 필요하지 않음)
    # 예측용 함수로 모든 계산을 하기 전에 대략적인 예측을 하여 가능성 높은곳만 계산하도록 도와줌
    return 0


# A* 알고리즘
def a_star(arg_congestion, arg_start, arg_goal):
    """경로를 계산하여 반환하는 함수"""
    pq = []
    heapq.heappush(pq, (0, arg_start))
    came_from = {arg_start: None}
    cost_so_far = {arg_start: 0}

    while pq:
        current = heapq.heappop(pq)[1]

        if current == arg_goal:
            break

        for next_node in arg_congestion[current]:
            new_cost = cost_so_far[current] + arg_congestion[current][next_node]
            if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                cost_so_far[next_node] = new_cost
                priority = new_cost + heuristic(arg_goal, next_node)
                heapq.heappush(pq, (priority, next_node))
                came_from[next_node] = current

    # 경로를 역추적하여 반환
    current = arg_goal
    result_path = []
    while current:
        result_path.append(current)
        current = came_from[current]
    result_path.reverse()

    return result_path


# 경로상에 추차할 구역이 있는지 확인하는 함수
def check_route(arg_route):
    print("check_route")
    print(arg_route)
    for walking_space_id in arg_route:
        for parking_space_id in walking_space[walking_space_id]["parking_space"]:
            if parking_space_id != -1 and parking_space[parking_space_id]["status"] == "empty":
                return walking_space_id, parking_space_id
    return None, None


def update_car_numbers_in_parking_space():
    """전송 전에 parking_space에 car_number 업데이트"""
    for space_id, space_data in parking_space.items():
        car_ids = parking_positions.get(space_id, [])
        car_numbers_list = [car_numbers[car_id]["car_number"] for car_id in car_ids if car_id in car_numbers]
        parking_space[space_id]["car_number"] = car_numbers_list if car_numbers_list else None


def del_target():
    """트래킹 실패한 경우를 대비 하여 이동 중인 차량이 없는 경우 모든 target과 해당 차량을 제거"""
    if len(walking_positions) == 0:
        for space_id, space_data in parking_space.items():
            if space_data["status"] == "target":
                space_data["status"] = "empty"
                del car_numbers[space_data["car_id"]]
                space_data["car_id"] = None

        # 이동 중인 차량이 없는 경우 주차 중인 아닌 차량 모두 제거
        for car_id in list(car_numbers.keys()):
            car_data = car_numbers[car_id]
            if car_data["status"] != "parking":
                del car_numbers[car_id]

        # 혼잡도를 기본값으로 초기화
        for node, connections in congestion.items():
            for neighbor in connections:
                congestion[node][neighbor] = 1

def set_parking_space_car_id(arg_parking_space_id, arg_car_id, arg_status):
    """
    주차 공간의 상태를 변경하는 함수.

    Args:
        arg_parking_space_id (int): 주차 공간 ID.
        arg_car_id (int): 차량 ID.
        arg_status (str): 주차 공간 상태. empty, target, occupied 중
    """

    # 출차의 경우에는 별도의 수정을 하지 않음
    if arg_parking_space_id == -1:
        return

    if arg_status == "empty":
        parking_space[arg_parking_space_id]["status"] = "empty"
        parking_space[arg_parking_space_id]["car_id"] = None
        parking_space[arg_parking_space_id]["entry_time"] = None
        parking_space[arg_parking_space_id]["parking_time"] = None

    elif arg_status == "target":
        parking_space[arg_parking_space_id]["status"] = "target"
        parking_space[arg_parking_space_id]["car_id"] = arg_car_id
        parking_space[arg_parking_space_id]["entry_time"] = car_numbers[arg_car_id]["entry_time"]
        parking_space[arg_parking_space_id]["parking_time"] = None

    elif arg_status == "occupied":
        parking_space[arg_parking_space_id]["status"] = "occupied"
        parking_space[arg_parking_space_id]["car_id"] = arg_car_id
        parking_space[arg_parking_space_id]["entry_time"] = car_numbers[arg_car_id]["entry_time"]
        parking_space[arg_parking_space_id]["parking_time"] = time.time()


def set_target(arg_car_id):
    """
    차량 ID를 받아 가장 가까운 주차 공간 ID를 반환하는 함수.

    Args:
        arg_car_id (int): 대상 차량 ID.

    Returns:
        int: 가장 가까운 주차 공간 ID 또는 -1 (주차 공간이 없는 경우)
    """
    # 차량이 이동 중인지 확인
    if arg_car_id not in walking_positions.values():
        print("차량이 이동 중이 아닙니다.")
        return

    # 현재 차량 위치
    current_x, current_y = car_numbers[arg_car_id]["position"]

    # 주차 공간 중 가장 가까운 빈 공간 찾기
    min_distance = float('inf')
    nearest_parking_space = None

    for space_id, space_data in parking_space.items():
        # 주차 공간이 비어 있는 경우만 고려
        if space_data["status"] == "empty":
            # 주차 공간의 중앙 좌표 계산
            space_x = (space_data["position"][0][0] + space_data["position"][2][0]) / 2
            space_y = (space_data["position"][0][1] + space_data["position"][2][1]) / 2

            # 현재 위치와 주차 공간 간 거리 계산
            distance = math.sqrt((current_x - space_x) ** 2 + (current_y - space_y) ** 2)

            if distance < min_distance:
                min_distance = distance
                nearest_parking_space = space_id

    if nearest_parking_space is not None:
        # 가장 가까운 주차 공간을 target 상태로 설정
        set_parking_space_car_id(nearest_parking_space, arg_car_id, "target")
        print(f"차량 {arg_car_id}의 가장 가까운 주차 공간: {nearest_parking_space}")
        return nearest_parking_space
    else:
        print("사용 가능한 주차 공간이 없습니다.")
        return -1


def reset_iteration_data():
    parking_positions.clear()
    walking_positions.clear()
    vehicles_to_route.clear()


if __name__ == "__main__":

    start = 0
    goal = 14

    path = a_star(congestion, start, goal)
    print(path)