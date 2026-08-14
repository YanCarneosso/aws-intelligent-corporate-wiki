"""Build a deterministic Lambda asset without requiring Docker during CDK synth."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build" / "lambda"


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    subprocess.run(  # noqa: S603 - executable and arguments are repository-controlled
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-compile",
            "--platform",
            "manylinux2014_aarch64",
            "--implementation",
            "cp",
            "--python-version",
            "3.12",
            "--abi",
            "cp312",
            "--only-binary=:all:",
            "--requirement",
            str(ROOT / "requirements-lambda.txt"),
            "--target",
            str(OUTPUT),
        ],
        check=True,
    )
    for package in ("services", "shared"):
        shutil.copytree(
            ROOT / package,
            OUTPUT / package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    print(f"lambda asset: {OUTPUT}")


if __name__ == "__main__":
    main()
