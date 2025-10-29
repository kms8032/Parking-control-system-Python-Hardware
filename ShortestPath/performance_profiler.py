"""
성능 측정을 위한 프로파일링 유틸리티

사용법:
    from performance_profiler import profiler

    with profiler.measure("작업명"):
        # 측정할 코드

    profiler.print_stats()
"""

import time
from contextlib import contextmanager
from collections import defaultdict
from typing import Dict, List

class PerformanceProfiler:
    def __init__(self):
        self.measurements: Dict[str, List[float]] = defaultdict(list)
        self.enabled = True

    @contextmanager
    def measure(self, label: str):
        """특정 코드 블록의 실행 시간을 측정"""
        if not self.enabled:
            yield
            return

        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000  # ms 단위
            self.measurements[label].append(elapsed)

    def print_stats(self, min_samples: int = 10):
        """수집된 통계를 출력"""
        if not self.measurements:
            print("📊 측정된 데이터가 없습니다.")
            return

        print("\n" + "="*70)
        print("📊 성능 프로파일링 결과")
        print("="*70)
        print(f"{'작업명':<30} {'평균(ms)':<12} {'최소(ms)':<12} {'최대(ms)':<12} {'샘플수':<10}")
        print("-"*70)

        # 평균 시간 기준으로 정렬
        sorted_items = sorted(
            self.measurements.items(),
            key=lambda x: sum(x[1])/len(x[1]),
            reverse=True
        )

        for label, times in sorted_items:
            if len(times) < min_samples:
                continue

            avg = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            count = len(times)

            print(f"{label:<30} {avg:>10.3f}  {min_time:>10.3f}  {max_time:>10.3f}  {count:>8}")

        print("="*70 + "\n")

    def reset(self):
        """측정 데이터 초기화"""
        self.measurements.clear()

    def enable(self):
        """프로파일링 활성화"""
        self.enabled = True

    def disable(self):
        """프로파일링 비활성화"""
        self.enabled = False

# 전역 프로파일러 인스턴스
profiler = PerformanceProfiler()
