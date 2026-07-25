import argparse
import json
from pathlib import Path
import sys

from app.agent.evaluation_protocol import (
    BlindEvaluationInvalid,
    compile_blind_comparison,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "tests" / "fixtures" / "agent_phase1_cases.json"


def approved_case_ids(path: Path) -> set[str]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    return {
        case["id"]
        for group in ("routingCases", "outputCases")
        for case in suite[group]
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile blind, content-free scores into a model comparison."
    )
    parser.add_argument("--assignments", required=True, type=Path)
    parser.add_argument("--scores", required=True, type=Path)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        comparison = compile_blind_comparison(
            json.loads(args.assignments.read_text(encoding="utf-8")),
            json.loads(args.scores.read_text(encoding="utf-8")),
            allowed_case_ids=approved_case_ids(args.cases),
        )
    except (
        BlindEvaluationInvalid,
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    rendered = json.dumps(comparison, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
