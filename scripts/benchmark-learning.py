import argparse
import json
from statistics import median
from time import perf_counter

from app.db.database import initialize_database
from app.learning import get_learning_service


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure local Learning service read latency.")
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--max-p95-ms", type=float)
    args = parser.parse_args()

    initialize_database()
    service = get_learning_service()
    operations = (
        ("roadmap", lambda: service.get_roadmap()),
        ("node", lambda: service.get_node("prompt")),
        ("search", lambda: service.search("RAG", 10)),
        ("agentContext", lambda: service.get_agent_context("RAG", 7)),
    )
    samples = []
    for _ in range(max(1, args.iterations)):
        for _, operation in operations:
            started = perf_counter()
            operation()
            samples.append((perf_counter() - started) * 1000)

    result = {
        "sampleCount": len(samples),
        "p50Ms": round(median(samples), 3),
        "p95Ms": round(percentile(samples, 0.95), 3),
        "maxMs": round(max(samples), 3),
    }
    print(json.dumps(result, ensure_ascii=False))
    return int(args.max_p95_ms is not None and result["p95Ms"] > args.max_p95_ms)


if __name__ == "__main__":
    raise SystemExit(main())
