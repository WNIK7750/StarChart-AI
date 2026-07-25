import argparse
from pathlib import Path
import sys

from app.agent.model_gate import ModelComparisonInvalid
from app.agent.model_report import (
    build_archive_metadata,
    build_decision_report,
    render_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a sanitized qwen3.5-flash vs qwen3.7-plus comparison."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--metadata-output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = args.input.read_bytes()
    try:
        report = build_decision_report(source)
    except (UnicodeDecodeError, ValueError, ModelComparisonInvalid) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
    rendered = render_json(report)

    if args.check:
        if not args.output:
            parser.error("--check requires --output")
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(
                "MODEL_DECISION_ARTIFACT_STALE: regenerate the committed decision report",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print("Agent model decision report is current.")
        return

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.metadata_output:
        args.metadata_output.write_text(
            render_json(build_archive_metadata(source, report)),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
