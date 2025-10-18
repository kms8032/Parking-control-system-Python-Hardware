"""
가장 가까운 주차 공간 찾기 테스트 코드
get_target_parking_space_id 함수의 다양한 테스트 케이스를 포함
"""

import sys
import os

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shortest_route import (
    ParkingSpace,
    get_target_parking_space_id,
    parking_space_instances,
    ParkingSpaceEnum,
    CarStatus
)


class TestTargetParkingSpace:
    """가장 가까운 주차 공간 찾기 테스트"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_cases = []

    def setup_parking_spaces(self):
        """테스트용 주차 공간 설정"""
        global parking_space_instances
        parking_space_instances.clear()

        # 주차 공간 1: 좌상단 (0, 0) ~ (100, 100)
        parking_space_instances[1] = ParkingSpace(
            space_id=1,
            name="P1",
            position=[(0, 0), (100, 0), (100, 100), (0, 100)],
            near_moving_space_id=1
        )
        parking_space_instances[1].status = ParkingSpaceEnum.EMPTY

        # 주차 공간 2: 중앙 (200, 200) ~ (300, 300)
        parking_space_instances[2] = ParkingSpace(
            space_id=2,
            name="P2",
            position=[(200, 200), (300, 200), (300, 300), (200, 300)],
            near_moving_space_id=2
        )
        parking_space_instances[2].status = ParkingSpaceEnum.EMPTY

        # 주차 공간 3: 우하단 (500, 500) ~ (600, 600)
        parking_space_instances[3] = ParkingSpace(
            space_id=3,
            name="P3",
            position=[(500, 500), (600, 500), (600, 600), (500, 600)],
            near_moving_space_id=3
        )
        parking_space_instances[3].status = ParkingSpaceEnum.EMPTY

        # 주차 공간 4: 좌하단 (0, 400) ~ (100, 500) - OCCUPIED
        parking_space_instances[4] = ParkingSpace(
            space_id=4,
            name="P4",
            position=[(0, 400), (100, 400), (100, 500), (0, 500)],
            near_moving_space_id=4
        )
        parking_space_instances[4].status = ParkingSpaceEnum.OCCUPIED

        # 주차 공간 5: 우상단 (400, 0) ~ (500, 100) - TARGET
        parking_space_instances[5] = ParkingSpace(
            space_id=5,
            name="P5",
            position=[(400, 0), (500, 0), (500, 100), (400, 100)],
            near_moving_space_id=5
        )
        parking_space_instances[5].status = ParkingSpaceEnum.TARGET

    def test_case(self, name, position, expected_space_id):
        """개별 테스트 케이스 실행"""
        result = get_target_parking_space_id(position, CarStatus.ENTRY)

        status = "✅ PASS" if result == expected_space_id else "❌ FAIL"

        if result == expected_space_id:
            self.passed += 1
        else:
            self.failed += 1

        self.test_cases.append({
            "name": name,
            "position": position,
            "expected": expected_space_id,
            "result": result,
            "status": status
        })

        print(f"{status} | {name}")
        print(f"   Position: {position}, Expected: {expected_space_id}, Got: {result}")

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 80)
        print("가장 가까운 주차 공간 찾기 테스트 시작")
        print("=" * 80)

        # 주차 공간 설정
        self.setup_parking_spaces()

        print("\n[주차 공간 상태]")
        for space_id, space in parking_space_instances.items():
            center = space.get_center_position()
            print(f"  P{space_id}: {space.name} - 중심({center[0]}, {center[1]}) - 상태: {space.status.value}")

        print("\n[테스트 케이스 실행]")

        # 테스트 케이스 1: 원점 근처 - P1이 가장 가까움
        self.test_case(
            "TC01: 원점 근처 (10, 10) -> P1",
            (10, 10),
            1
        )

        # 테스트 케이스 2: P1 중심 근처
        self.test_case(
            "TC02: P1 중심 (50, 50) -> P1",
            (50, 50),
            1
        )

        # 테스트 케이스 3: P2 중심 근처
        self.test_case(
            "TC03: P2 중심 (250, 250) -> P2",
            (250, 250),
            2
        )

        # 테스트 케이스 4: P3 중심 근처
        self.test_case(
            "TC04: P3 중심 (550, 550) -> P3",
            (550, 550),
            3
        )

        # 테스트 케이스 5: P1과 P2 사이 - P1이 더 가까움
        self.test_case(
            "TC05: P1과 P2 사이 (150, 150) -> P1",
            (150, 150),
            1
        )

        # 테스트 케이스 6: P2와 P3 사이 - P2가 더 가까움
        self.test_case(
            "TC06: P2와 P3 사이 (400, 400) -> P2",
            (400, 400),
            2
        )

        # 테스트 케이스 7: P4는 OCCUPIED 상태이므로 선택되지 않음
        self.test_case(
            "TC07: P4 중심이지만 OCCUPIED (50, 450) -> P2",
            (50, 450),
            2
        )

        # 테스트 케이스 8: P5는 TARGET 상태이므로 선택되지 않음
        self.test_case(
            "TC08: P5 중심이지만 TARGET (450, 50) -> P2",
            (450, 50),
            2
        )

        # 테스트 케이스 9: 모든 주차 공간을 OCCUPIED로 변경
        print("\n[모든 주차 공간을 OCCUPIED로 변경]")
        for space in parking_space_instances.values():
            space.status = ParkingSpaceEnum.OCCUPIED

        self.test_case(
            "TC09: 모든 공간이 차있을 때 (100, 100) -> -1",
            (100, 100),
            -1
        )

        # 테스트 케이스 10: 주차 공간 복원 후 매우 먼 거리
        print("\n[주차 공간 상태 복원]")
        self.setup_parking_spaces()

        self.test_case(
            "TC10: 매우 먼 거리 (1000, 1000) -> P3",
            (1000, 1000),
            3
        )

        # 테스트 케이스 11: 음수 좌표
        self.test_case(
            "TC11: 음수 좌표 (-50, -50) -> P1",
            (-50, -50),
            1
        )

        # 테스트 케이스 12: P1만 EMPTY로 설정
        print("\n[P1만 EMPTY 상태로 설정]")
        parking_space_instances[1].status = ParkingSpaceEnum.EMPTY
        parking_space_instances[2].status = ParkingSpaceEnum.OCCUPIED
        parking_space_instances[3].status = ParkingSpaceEnum.OCCUPIED

        self.test_case(
            "TC12: P1만 비어있을 때 P3 근처 (550, 550) -> P1",
            (550, 550),
            1
        )

        # 테스트 케이스 13: P3만 EMPTY로 설정
        print("\n[P3만 EMPTY 상태로 설정]")
        parking_space_instances[1].status = ParkingSpaceEnum.OCCUPIED
        parking_space_instances[2].status = ParkingSpaceEnum.OCCUPIED
        parking_space_instances[3].status = ParkingSpaceEnum.EMPTY

        self.test_case(
            "TC13: P3만 비어있을 때 P1 근처 (50, 50) -> P3",
            (50, 50),
            3
        )

        # 테스트 케이스 14: 경계값 테스트 (0, 0)
        print("\n[전체 주차 공간 복원]")
        self.setup_parking_spaces()

        self.test_case(
            "TC14: 경계값 (0, 0) -> P1",
            (0, 0),
            1
        )

        # 테스트 케이스 15
        self.test_case(
            "TC15",
            (175, 175),
            2
        )

        print("\n[모든 주차 공간을 EMPTY로 변경]")
        for space in parking_space_instances.values():
            space.status = ParkingSpaceEnum.EMPTY
        
        # 테스트 케이스 16
        self.test_case(
            "TC16",
            (700, 50),
            5
        )

        # 테스트 케이스 17
        self.test_case(
            "TC17",
            (200, 600),
            4
        )

        # 테스트 케이스 18
        self.test_case(
            "TC18",
            (-100, 900),
            4
        )

        parking_space_instances[4].status = ParkingSpaceEnum.OCCUPIED

        # 테스트 케이스 19
        self.test_case(
            "TC18",
            (-100, 900),
            2   # 2번과 3번이 동일하여 2번이 선택
        )
        

        # 결과 출력
        print("\n" + "=" * 80)
        print("테스트 결과 요약")
        print("=" * 80)
        print(f"총 테스트: {self.passed + self.failed}개")
        print(f"✅ 통과: {self.passed}개")
        print(f"❌ 실패: {self.failed}개")
        print(f"성공률: {(self.passed / (self.passed + self.failed) * 100):.2f}%")
        print("=" * 80)

        # 실패한 테스트 케이스 상세 정보
        if self.failed > 0:
            print("\n실패한 테스트 케이스:")
            for tc in self.test_cases:
                if tc["status"] == "❌ FAIL":
                    print(f"\n  {tc['name']}")
                    print(f"  Position: {tc['position']}")
                    print(f"  Expected: {tc['expected']}, Got: {tc['result']}")


if __name__ == "__main__":
    tester = TestTargetParkingSpace()
    tester.run_all_tests()
