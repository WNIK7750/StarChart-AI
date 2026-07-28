import argparse
import json
from pathlib import Path
import sys

from app.agent.evaluation_protocol import build_blind_protocol_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = (
    ROOT
    / "docs"
    / "06-evidence"
    / "agent"
    / "agent_blind_evaluation_protocol_manifest.json"
)


def rendered_manifest() -> str:
    return (
        json.dumps(
            build_blind_protocol_manifest(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build or check the content-free Agent blind evaluation protocol."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = rendered_manifest()

    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(
                "BLIND_EVAL_PROTOCOL_ARTIFACT_STALE: regenerate the committed protocol manifest",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print("Agent blind evaluation protocol manifest is current.")
        return

    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
