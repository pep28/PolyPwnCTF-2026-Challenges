#!/usr/bin/env python3
"""Run one solution and check that it prints the challenge flag."""
from pathlib import Path
import re
import subprocess
import sys
import time

import yaml


def read_flags(challenge_dir):
    data = yaml.safe_load((challenge_dir / "challenge.yml").read_text(encoding="utf-8"))
    flags = data["flags"]
    if isinstance(flags, str):
        return [flags]
    return [flag if isinstance(flag, str) else flag["content"] for flag in flags]


def main():
    if len(sys.argv) != 3:
        print("Usage: check_solution.py CHALLENGE_DIR SOLUTION", file=sys.stderr)
        return 2

    challenge_dir = Path(sys.argv[1]).resolve()
    solution = (Path.cwd() / sys.argv[2]).resolve()
    flags = read_flags(challenge_dir)
    last_error = ""

    for attempt in range(5):
        try:
            result = subprocess.run(
                [sys.executable, str(solution)],
                cwd=challenge_dir,
                capture_output=True,
                text=True,
                timeout=90,
            )
        except subprocess.TimeoutExpired:
            last_error = "solution timed out"
        else:
            output = result.stdout + result.stderr
            if result.returncode == 0 and any(
                re.search(r"(?<![\w{])" + re.escape(flag) + r"(?![\w}])", output)
                for flag in flags
            ):
                print(f"Solution validée: {challenge_dir.name}")
                return 0
            last_error = f"exit={result.returncode}"

        if attempt < 4:
            time.sleep(2)

    print(f"Solution invalide pour {challenge_dir}: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
