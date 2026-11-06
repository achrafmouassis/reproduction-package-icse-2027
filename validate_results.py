"""Check paired Maven build reports before aggregating benchmark results."""

import argparse
import json
import re
import sys
from pathlib import Path


def report_problem(path: Path) -> str | None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "report is missing"
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "report is not valid UTF-8 JSON"
    except OSError as error:
        return f"cannot read report ({error.strerror})"

    if not isinstance(report, dict) or "error" in report:
        return "expected a profiling report without an error"
    exit_code = report.get("exit_code")
    if type(exit_code) is not int:
        return "expected an integer Maven exit_code"
    if exit_code != 0:
        return f"Maven exited with status {exit_code}"
    phases = report.get("phases")
    if not isinstance(phases, list) or not phases:
        return "expected a non-empty phases list"
    return None


def validate_results(root: Path) -> tuple[int, list[str]]:
    """Count valid pairs and list problems in the iteration directories present."""
    valid_pairs = 0
    problems = []
    for iteration in sorted(root.glob("*/iter_*")):
        if not iteration.is_dir() or not re.fullmatch(r"iter_[0-9]+", iteration.name):
            continue

        pair_problems = []
        for build_type in ("cold", "warm"):
            path = iteration / f"{build_type}_build.json"
            problem = report_problem(path)
            if problem is not None:
                pair_problems.append(f"{path.relative_to(root).as_posix()}: {problem}")

        if pair_problems:
            problems.extend(pair_problems)
        else:
            valid_pairs += 1

    if not valid_pairs and not problems:
        problems.append(f"{root}: no benchmark iterations found (expected <version>/iter_<n>)")
    return valid_pairs, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_dir", type=Path, help="extracted results directory")
    args = parser.parse_args()
    valid_pairs, problems = validate_results(args.results_dir)
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"Valid cold/warm pairs: {valid_pairs}")
    return int(bool(problems))


if __name__ == "__main__":
    sys.exit(main())
