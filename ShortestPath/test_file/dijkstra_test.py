"""
다익스트라 알고리즘 테스트 코드
shortest_route.py의 dijkstra 함수에 대한 포괄적인 테스트 케이스를 포함
"""

import sys
import os

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shortest_route import dijkstra, MovingSpace, moving_space_instances


class TestDijkstra:
    """다익스트라 알고리즘 테스트"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_cases = []

    def setup_test_graph(self):
        """테스트용 그래프 설정"""
        # 기존 인스턴스 초기화
        moving_space_instances.clear()

        # 테스트용 MovingSpace 인스턴스 생성
        # 간단한 그래프: 1 -> 2 -> 3 -> 4
        #                   |    |
        #                   v    v
        #                   5 -> 6

        moving_space_instances[1] = MovingSpace(
            space_id=1,
            name="space_1",
            position=[(0, 0), (10, 0), (10, 10), (0, 10)],
            congestion=100,
            near_parking_space_id=[],
            near_moving_space_id=[2, 5]
        )
        moving_space_instances[2] = MovingSpace(
            space_id=2,
            name="space_2",
            position=[(10, 0), (20, 0), (20, 10), (10, 10)],
            congestion=100,
            near_parking_space_id=[],
            near_moving_space_id=[1, 3, 6]
        )
        moving_space_instances[3] = MovingSpace(
            space_id=3,
            name="space_3",
            position=[(20, 0), (30, 0), (30, 10), (20, 10)],
            congestion=100,
            near_parking_space_id=[],
            near_moving_space_id=[2, 4]
        )
        moving_space_instances[4] = MovingSpace(
            space_id=4,
            name="space_4",
            position=[(30, 0), (40, 0), (40, 10), (30, 10)],
            congestion=100,
            near_parking_space_id=[],
            near_moving_space_id=[3]
        )
        moving_space_instances[5] = MovingSpace(
            space_id=5,
            name="space_5",
            position=[(0, 10), (10, 10), (10, 20), (0, 20)],
            congestion=100,
            near_parking_space_id=[],
            near_moving_space_id=[1, 6]
        )
        moving_space_instances[6] = MovingSpace(
            space_id=6,
            name="space_6",
            position=[(10, 10), (20, 10), (20, 20), (10, 20)],
            congestion=100,
            near_parking_space_id=[],
            near_moving_space_id=[2, 5]
        )

    def setup_complex_graph(self):
        """복잡한 테스트용 그래프 설정 (실제 주차장 구조)"""
        moving_space_instances.clear()

        # 실제 주차장 구조 기반 연결
        graph_data = {
            1: {"position": [[1090, 505], [1336, 492], [1443, 886], [1147, 889]], "neighbors": [2], "congestion": 100},
            2: {"position": [[815, 532], [1094, 531], [1125, 744], [810, 720]], "neighbors": [1, 3, 5], "congestion": 200},
            3: {"position": [[559, 526], [823, 525], [817, 717], [531, 719]], "neighbors": [2, 4], "congestion": 100},
            4: {"position": [[385, 521], [568, 523], [539, 727], [334, 730]], "neighbors": [3, 6], "congestion": 100},
            5: {"position": [[816, 372], [1066, 373], [1100, 538], [807, 535]], "neighbors": [2, 7], "congestion": 100},
            6: {"position": [[417, 369], [578, 375], [564, 531], [381, 529]], "neighbors": [4, 9], "congestion": 100},
            7: {"position": [[814, 237], [1049, 236], [1067, 383], [811, 379]], "neighbors": [5, 8, 10], "congestion": 100},
            8: {"position": [[595, 234], [820, 231], [813, 377], [578, 375]], "neighbors": [7, 9], "congestion": 100},
            9: {"position": [[445, 241], [599, 242], [580, 382], [412, 377]], "neighbors": [6, 8, 11], "congestion": 100},
            10: {"position": [[818, 115], [1035, 113], [1049, 246], [812, 244]], "neighbors": [7, 12], "congestion": 100},
            11: {"position": [[472, 122], [608, 120], [595, 245], [439, 247]], "neighbors": [9, 14], "congestion": 100},
            12: {"position": [[824, 8], [1029, 4], [1037, 121], [820, 123]], "neighbors": [10, 13, 15], "congestion": 100},
            13: {"position": [[613, 12], [835, 6], [824, 106], [608, 107]], "neighbors": [12, 14], "congestion": 100},
            14: {"position": [[487, 7], [628, 6], [611, 129], [468, 128]], "neighbors": [11, 13], "congestion": 100},
            15: {"position": [[1028, 5], [1226, 9], [1244, 136], [1031, 138]], "neighbors": [12], "congestion": 100}
        }

        for space_id, data in graph_data.items():
            moving_space_instances[space_id] = MovingSpace(
                space_id=space_id,
                name=f"Path_{space_id}",
                position=[(p[0], p[1]) for p in data["position"]],
                congestion=data["congestion"],
                near_parking_space_id=[],
                near_moving_space_id=data["neighbors"]
            )

    def test_case(self, name, start_id, goal_id, expected_path):
        """개별 테스트 케이스 실행"""
        try:
            result_path = dijkstra(start_id, goal_id)

            # 경로가 예상과 일치하는지 확인
            is_match = result_path == expected_path

            # 경로의 시작과 끝이 올바른지 확인
            is_valid_start = result_path[0] == start_id if result_path else False
            is_valid_end = result_path[-1] == goal_id if result_path else False

            # 경로가 연결되어 있는지 확인
            is_connected = self.verify_path_connectivity(result_path)

            success = is_match and is_valid_start and is_valid_end and is_connected
            status = "✅ PASS" if success else "❌ FAIL"

            if success:
                self.passed += 1
            else:
                self.failed += 1

            self.test_cases.append({
                "name": name,
                "start_id": start_id,
                "goal_id": goal_id,
                "expected": expected_path,
                "result": result_path,
                "status": status,
                "is_connected": is_connected
            })

            print(f"{status} | {name}")
            print(f"   Start: {start_id}, Goal: {goal_id}")
            print(f"   Expected: {expected_path}")
            print(f"   Got:      {result_path}")
            if not is_connected:
                print(f"   ⚠️  경로 연결성 검증 실패")

        except Exception as e:
            self.failed += 1
            print(f"❌ FAIL | {name}")
            print(f"   Error: {e}")
            self.test_cases.append({
                "name": name,
                "start_id": start_id,
                "goal_id": goal_id,
                "expected": expected_path,
                "result": None,
                "status": "❌ FAIL",
                "error": str(e)
            })

    def verify_path_connectivity(self, path):
        """경로의 연결성을 검증 (각 노드가 다음 노드와 실제로 연결되어 있는지)"""
        if not path or len(path) < 2:
            return True

        for i in range(len(path) - 1):
            current = path[i]
            next_node = path[i + 1]

            # 현재 노드가 다음 노드와 연결되어 있는지 확인
            if next_node not in moving_space_instances[current].near_moving_space_id:
                return False

        return True

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 80)
        print("다익스트라 알고리즘 테스트 시작")
        print("=" * 80)

        # 기본 그래프 테스트
        print("\n[기본 그래프 테스트]")
        self.setup_test_graph()

        # TC01: 직선 경로 (1 -> 4)
        self.test_case(
            "TC01: 직선 경로 테스트 (1 -> 4)",
            1, 4,
            [1, 2, 3, 4]
        )

        # TC02: 짧은 경로 (1 -> 2)
        self.test_case(
            "TC02: 인접 노드 경로 (1 -> 2)",
            1, 2,
            [1, 2]
        )

        # TC03: 우회 경로 (1 -> 6)
        self.test_case(
            "TC03: 우회 경로 테스트 (1 -> 6)",
            1, 6,
            [1, 2, 6]
        )

        # TC04: 시작점과 목표점이 동일
        self.test_case(
            "TC04: 시작점과 목표점 동일 (3 -> 3)",
            3, 3,
            [3]
        )

        # TC05: 역방향 경로 (4 -> 1)
        self.test_case(
            "TC05: 역방향 경로 (4 -> 1)",
            4, 1,
            [4, 3, 2, 1]
        )

        # TC06: 하단 경로 (5 -> 6)
        self.test_case(
            "TC06: 하단 경로 (5 -> 6)",
            5, 6,
            [5, 6]
        )

        # TC07: 대각선 경로 (1 -> 6)
        self.test_case(
            "TC07: 대각선 경로 (1 -> 6)",
            1, 6,
            [1, 2, 6]
        )

        # 복잡한 그래프 테스트 (실제 주차장 구조)
        print("\n[복잡한 그래프 테스트 - 실제 주차장 구조]")
        self.setup_complex_graph()

        # TC08: 입구에서 출구까지 (1 -> 15)
        self.test_case(
            "TC08: 입구에서 출구까지 (1 -> 15)",
            1, 15,
            [1, 2, 5, 7, 10, 12, 15]
        )

        # TC09: 중간 경로 (2 -> 14)
        self.test_case(
            "TC09: 중간 경로 테스트 (2 -> 14)",
            2, 14,
            [2, 3, 4, 6, 9, 11, 14]
        )

        # TC10: 짧은 경로 (7 -> 10)
        self.test_case(
            "TC10: 짧은 경로 (7 -> 10)",
            7, 10,
            [7, 10]
        )

        # TC11: 우측 경로 (4 -> 9)
        self.test_case(
            "TC11: 우측 경로 (4 -> 9)",
            4, 9,
            [4, 6, 9]
        )

        # TC12: 좌측에서 우측으로 (1 -> 14)
        self.test_case(
            "TC12: 좌측에서 우측으로 (1 -> 14)",
            1, 14,
            [1, 2, 3, 4, 6, 9, 11, 14]
        )

        # 혼잡도 변화 테스트
        print("\n[혼잡도 변화 테스트]")

        # TC13: 특정 구역의 혼잡도 증가 후 경로 변경 확인
        self.setup_complex_graph()
        # 구역 2의 혼잡도를 크게 증가
        moving_space_instances[2].congestion = 10000

        self.test_case(
            "TC13: 혼잡도 높은 구역 우회 (1 -> 5)",
            1, 5,
            [1, 2, 5]  # 여전히 2를 거쳐야 하지만 비용이 높아짐
        )

        # TC14: 여러 구역의 혼잡도 증가
        self.setup_complex_graph()
        moving_space_instances[5].congestion = 800
        moving_space_instances[13].congestion = 800

        self.test_case(
            "TC14: 여러 구역 혼잡도 증가 (1 -> 12)",
            1, 12,
            [1, 2, 3, 4, 6, 9, 8, 7, 10, 12]
        )

        # 엣지 케이스 테스트
        print("\n[엣지 케이스 테스트]")
        self.setup_test_graph()

        # TC15: 시작점 = 끝점 (경로 길이 1)
        self.test_case(
            "TC15: 시작점과 끝점이 같음 (1 -> 1)",
            1, 1,
            [1]
        )

        # TC16: 인접 노드로의 이동
        self.test_case(
            "TC16: 인접 노드 이동 (3 -> 4)",
            3, 4,
            [3, 4]
        )

        # TC17: 최장 경로 (1 -> 4, 우회 없이)
        self.test_case(
            "TC17: 최장 직선 경로 (1 -> 4)",
            1, 4,
            [1, 2, 3, 4]
        )

        self.setup_complex_graph()
        moving_space_instances[3].congestion = 500

        self.test_case(
            "TC18: 3번 구역 혼잡으로 우회 경로",
            5, 4,
            [5, 7, 8, 9, 6, 4]
        )

        moving_space_instances[8].congestion = 500

        self.test_case(
            "TC19: 8번 구역도 혼잡해져서 3번 선택",
            5, 4,
            [5, 2, 3, 4]
        )

        moving_space_instances[3].congestion = 1000
        moving_space_instances[8].congestion = 501
        
        self.test_case(
            "TC20: 3번, 8번 혼잡해져서 우회 경로",
            5, 4,
            [5, 7, 10, 12, 13, 14, 11, 9, 6, 4]
        )

        # 성능 테스트
        print("\n[성능 테스트]")
        self.setup_complex_graph()

        import time
        start_time = time.time()

        # 여러 경로를 빠르게 계산
        for _ in range(100):
            dijkstra(1, 15)

        end_time = time.time()
        elapsed_time = end_time - start_time

        print(f"100회 경로 계산 시간: {elapsed_time:.4f}초")
        print(f"평균 계산 시간: {elapsed_time/100*1000:.2f}ms")

        # 결과 출력
        print("\n" + "=" * 80)
        print("테스트 결과 요약")
        print("=" * 80)
        print(f"총 테스트: {self.passed + self.failed}개")
        print(f"✅ 통과: {self.passed}개")
        print(f"❌ 실패: {self.failed}개")
        if self.passed + self.failed > 0:
            print(f"성공률: {(self.passed / (self.passed + self.failed) * 100):.2f}%")
        print("=" * 80)

        # 실패한 테스트 케이스 상세 정보
        if self.failed > 0:
            print("\n실패한 테스트 케이스:")
            for tc in self.test_cases:
                if tc["status"] == "❌ FAIL":
                    print(f"\n  {tc['name']}")
                    print(f"  Start: {tc['start_id']}, Goal: {tc['goal_id']}")
                    print(f"  Expected: {tc['expected']}")
                    print(f"  Got:      {tc.get('result', 'Error occurred')}")
                    if 'error' in tc:
                        print(f"  Error: {tc['error']}")
                    if not tc.get('is_connected', True):
                        print(f"  Issue: 경로의 연결성 검증 실패")


if __name__ == "__main__":
    tester = TestDijkstra()
    tester.run_all_tests()
