import argparse
import json
from pathlib import Path
import sys

from app.agent.evaluation_manifest import (
    EvaluationManifestInvalid,
    build_evaluation_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "tests" / "fixtures" / "agent_phase1_cases.json"
DEFAULT_ARTIFACT = (
    ROOT / "docs" / "06-evidence" / "agent" / "agent_phase1_evaluation_manifest.json"
)


def rendered_manifest(source: Path) -> str:
    document = json.loads(source.read_text(encoding="utf-8"))
    return (
        json.dumps(
            build_evaluation_manifest(document),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build or check the content-free Agent phase 1 evaluation manifest."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        rendered = rendered_manifest(args.input)
    except (EvaluationManifestInvalid, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(
                "EVAL_ARTIFACT_STALE: regenerate the committed evaluation manifest",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print("Agent evaluation manifest is current.")
        return

    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
