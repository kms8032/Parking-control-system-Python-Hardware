"""
사각형 내부 점 판별 테스트 코드
Space 클래스의 is_car_in_space 메소드에 대한 다양한 테스트 케이스를 포함
"""

import sys
import os

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shortest_route import Space


class TestPointInRectangle:
    """사각형 내부 점 판별 테스트"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_cases = []

    def test_case(self, name, point, rectangle, expected):
        """개별 테스트 케이스 실행"""
        # Space 인스턴스 생성
        space = Space(space_id=999, name="test_space", position=rectangle)

        # is_car_in_space 메소드 호출
        result = space.is_car_in_space(point[0], point[1])
        status = "✅ PASS" if result == expected else "❌ FAIL"

        if result == expected:
            self.passed += 1
        else:
            self.failed += 1

        self.test_cases.append({
            "name": name,
            "point": point,
            "rectangle": rectangle,
            "expected": expected,
            "result": result,
            "status": status
        })

        print(f"{status} | {name}")
        print(f"   Point: {point}, Expected: {expected}, Got: {result}")

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 80)
        print("사각형 내부 점 판별 테스트 시작")
        print("=" * 80)

        # 테스트 케이스 1: 정사각형 중심점
        rectangle_square = [(0, 0), (100, 0), (100, 100), (0, 100)]
        self.test_case(
            "TC01: 정사각형 중심점 (내부)",
            (50, 50),
            rectangle_square,
            True
        )

        # 테스트 케이스 2: 정사각형 좌상단 꼭짓점
        self.test_case(
            "TC02: 정사각형 좌상단 꼭짓점 (경계)",
            (0, 0),
            rectangle_square,
            True
        )

        # 테스트 케이스 3: 정사각형 우하단 꼭짓점
        self.test_case(
            "TC03: 정사각형 우하단 꼭짓점 (경계)",
            (100, 100),
            rectangle_square,
            True
        )

        # 테스트 케이스 4: 정사각형 외부 (왼쪽)
        self.test_case(
            "TC04: 정사각형 외부 왼쪽",
            (-10, 50),
            rectangle_square,
            False
        )

        # 테스트 케이스 5: 정사각형 외부 (오른쪽)
        self.test_case(
            "TC05: 정사각형 외부 오른쪽",
            (110, 50),
            rectangle_square,
            False
        )

        # 테스트 케이스 6: 정사각형 외부 (위)
        self.test_case(
            "TC06: 정사각형 외부 위",
            (50, -10),
            rectangle_square,
            False
        )

        # 테스트 케이스 7: 정사각형 외부 (아래)
        self.test_case(
            "TC07: 정사각형 외부 아래",
            (50, 110),
            rectangle_square,
            False
        )

        # 테스트 케이스 8: 정사각형 모서리 근처 (내부)
        self.test_case(
            "TC08: 정사각형 모서리 근처 내부",
            (5, 5),
            rectangle_square,
            True
        )

        # 테스트 케이스 9: 정사각형 모서리 근처 (외부)
        self.test_case(
            "TC09: 정사각형 모서리 근처 외부",
            (-5, -5),
            rectangle_square,
            False
        )

        # 테스트 케이스 10: 직사각형 (가로로 긴) 중심점
        rectangle_horizontal = [(0, 0), (200, 0), (200, 50), (0, 50)]
        self.test_case(
            "TC10: 가로 직사각형 중심점 (내부)",
            (100, 25),
            rectangle_horizontal,
            True
        )

        # 테스트 케이스 11: 직사각형 (세로로 긴) 중심점
        rectangle_vertical = [(0, 0), (50, 0), (50, 200), (0, 200)]
        self.test_case(
            "TC11: 세로 직사각형 중심점 (내부)",
            (25, 100),
            rectangle_vertical,
            True
        )

        # 테스트 케이스 12: 기울어진 사각형 (회전된 정사각형) 중심점
        rectangle_rotated = [(50, 0), (100, 50), (50, 100), (0, 50)]
        self.test_case(
            "TC12: 회전된 사각형 중심점 (내부)",
            (50, 50),
            rectangle_rotated,
            True
        )

        # 테스트 케이스 13: 기울어진 사각형 외부
        self.test_case(
            "TC13: 회전된 사각형 외부",
            (10, 10),
            rectangle_rotated,
            False
        )

        # 테스트 케이스 14: 실제 주차 구역 좌표 (parking_space.json 기반)
        # 주차 구역 16번 좌표
        parking_16 = [(53, 21), (127, 16), (131, 63), (58, 67)]
        self.test_case(
            "TC14: 실제 주차구역 16번 내부",
            (90, 40),
            parking_16,
            True
        )

        # 테스트 케이스 15: 실제 주차 구역 외부
        self.test_case(
            "TC15: 실제 주차구역 16번 외부",
            (30, 30),
            parking_16,
            False
        )

        # 테스트 케이스 16: 실제 이동 구역 좌표 (walking_space.json 기반)
        # 이동 구역 2번 좌표
        walking_2 = [(130, 20), (407, 14), (405, 67), (134, 71)]
        self.test_case(
            "TC16: 실제 이동구역 2번 내부",
            (270, 40),
            walking_2,
            True
        )

        # 테스트 케이스 17: 실제 이동 구역 외부
        self.test_case(
            "TC17: 실제 이동구역 2번 외부",
            (100, 40),
            walking_2,
            False
        )

        # 테스트 케이스 18: 매우 작은 사각형
        small_rectangle = [(0, 0), (1, 0), (1, 1), (0, 1)]
        self.test_case(
            "TC18: 매우 작은 사각형 내부",
            (0.5, 0.5),
            small_rectangle,
            True
        )

        # 테스트 케이스 19: 매우 큰 사각형
        large_rectangle = [(0, 0), (10000, 0), (10000, 10000), (0, 10000)]
        self.test_case(
            "TC19: 매우 큰 사각형 내부",
            (5000, 5000),
            large_rectangle,
            True
        )

        # 테스트 케이스 20: 음수 좌표를 포함한 사각형
        negative_rectangle = [(-100, -100), (100, -100), (100, 100), (-100, 100)]
        self.test_case(
            "TC20: 음수 좌표 사각형 중심점 (내부)",
            (0, 0),
            negative_rectangle,
            True
        )

        # 테스트 케이스 21: 음수 좌표 사각형 외부
        self.test_case(
            "TC21: 음수 좌표 사각형 외부",
            (-150, 0),
            negative_rectangle,
            False
        )

        # 테스트 케이스 22: 경계선 상의 점 (상단)
        self.test_case(
            "TC22: 정사각형 상단 경계선",
            (50, 0),
            rectangle_square,
            True
        )

        # 테스트 케이스 23: 경계선 상의 점 (우측)
        self.test_case(
            "TC23: 정사각형 우측 경계선",
            (100, 50),
            rectangle_square,
            True
        )

        # 테스트 케이스 24: 평행사변형 (일반 사각형)
        parallelogram = [(0, 0), (100, 20), (120, 100), (20, 80)]
        self.test_case(
            "TC24: 평행사변형 내부",
            (60, 50),
            parallelogram,
            True
        )

        # 테스트 케이스 25: 평행사변형 내부
        self.test_case(
            "TC25: 평행사변형 내부",
            (10, 10),
            parallelogram,
            True
        )

        # 테스트 케이스 26: 평행사변형 외부
        self.test_case(
            "TC26: 평행사변형 외부",
            (-10, 10),
            parallelogram,
            False
        )

        # 테스트 케이스 27: 평행사변형 외부
        self.test_case(
            "TC27: 평행사변형 외부",
            (10, 60),
            parallelogram,
            False
        )

        # 테스트 케이스 28: 평행사변형 꼭짓점
        self.test_case(
            "TC28: 평행사변형 꼭짓점",
            (100, 120),
            parallelogram,
            False
        )

        # 테스트 케이스 29: 평행사변형 내부
        self.test_case(
            "TC29: 평행사변형 내부",
            (70, 15),
            parallelogram,
            True
        )

        # 테스트 케이스 30: 평행사변형 경계
        self.test_case(
            "TC30: 평행사변형 경계",
            (100.5, 22),
            parallelogram,
            True
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
                    print(f"  Point: {tc['point']}")
                    print(f"  Rectangle: {tc['rectangle']}")
                    print(f"  Expected: {tc['expected']}, Got: {tc['result']}")


if __name__ == "__main__":
    tester = TestPointInRectangle()
    tester.run_all_tests()