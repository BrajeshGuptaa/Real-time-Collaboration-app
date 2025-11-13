from __future__ import annotations

import statistics
from typing import Dict, List


class QueueMetrics:
    def __init__(self) -> None:
        self.status_counts: Dict[str, int] = {
            "queued": 0,
            "running": 0,
            "succeeded": 0,
            "failed": 0,
            "dead": 0,
        }
        self.retries: int = 0
        self.latencies_ms: List[float] = []

    def record_status(self, status: str) -> None:
        self.status_counts[status] = self.status_counts.get(status, 0) + 1

    def record_retry(self) -> None:
        self.retries += 1

    def record_latency(self, latency_ms: float) -> None:
        self.latencies_ms.append(latency_ms)

    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_samples = sorted(self.latencies_ms)
        k = int(0.95 * (len(sorted_samples) - 1))
        return float(sorted_samples[k])

    def summary(self) -> Dict[str, float | int]:
        return {
            "retries": self.retries,
            "p95_latency_ms": self.p95_latency_ms(),
            **self.status_counts,
        }
