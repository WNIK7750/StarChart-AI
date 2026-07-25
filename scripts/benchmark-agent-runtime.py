import argparse
import asyncio
from itertools import cycle
import json
import logging
from math import ceil
from platform import machine, python_version
from time import perf_counter

from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import AgentChatRequest
from app.core.config import AGENT_RUNTIME_STATE_BACKEND, API_WORKERS


BENCHMARK_MESSAGES = (
    "介绍 RAG",
    "推荐一个编程工具",
    "设置页面在哪里",
    "给我一条提示词工程学习路线",
    "设计一套论文阅读工作流",
)


def percentile(values: list[float], value: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * value) - 1)]


async def benchmark(samples: int, concurrency: int, max_p95_ms: float) -> dict:
    orchestrator = AgentOrchestrator()
    semaphore = asyncio.Semaphore(concurrency)
    messages = cycle(BENCHMARK_MESSAGES)

    async def one(index: int) -> float:
        request = AgentChatRequest(message=next(messages))
        started = perf_counter()
        async with semaphore:
            response = await orchestrator.respond(
                request,
                request_id=f"offline-benchmark-{index}",
            )
        if not response.answer:
            raise RuntimeError("deterministic Agent returned an empty answer")
        return (perf_counter() - started) * 1000

    started = perf_counter()
    latencies = await asyncio.gather(*(one(index) for index in range(samples)))
    duration_seconds = perf_counter() - started
    p95_ms = percentile(latencies, 0.95)
    return {
        "version": "agent-runtime-baseline-v1",
        "mode": "deterministic",
        "networkCalls": False,
        "samples": samples,
        "concurrency": concurrency,
        "durationSeconds": round(duration_seconds, 4),
        "throughputPerSecond": round(samples / duration_seconds, 2),
        "latencyMs": {
            "p50": round(percentile(latencies, 0.5), 2),
            "p95": round(p95_ms, 2),
            "max": round(max(latencies), 2),
        },
        "thresholds": {
            "maxP95Ms": max_p95_ms,
            "passed": p95_ms <= max_p95_ms,
        },
        "runtime": {
            "declaredWorkers": API_WORKERS,
            "agentStateBackend": AGENT_RUNTIME_STATE_BACKEND,
            "python": python_version(),
            "machine": machine(),
        },
        "meta": {
            "containsPii": False,
            "containsPrompts": False,
            "containsResponses": False,
            "comparableOnlyOnSameHostClass": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline single-process Agent runtime baseline."
    )
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-p95-ms", type=float, default=1500)
    args = parser.parse_args()
    if not 10 <= args.samples <= 500:
        raise SystemExit("--samples must be between 10 and 500")
    if not 1 <= args.concurrency <= 32:
        raise SystemExit("--concurrency must be between 1 and 32")
    if args.max_p95_ms <= 0:
        raise SystemExit("--max-p95-ms must be positive")

    logging.getLogger("app.agent.provider").setLevel(logging.CRITICAL)
    report = asyncio.run(
        benchmark(args.samples, args.concurrency, args.max_p95_ms)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["thresholds"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
