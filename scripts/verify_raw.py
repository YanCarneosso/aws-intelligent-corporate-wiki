"""Fail when the challenge's original raw files differ by one byte."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("raw-manifest.json")


def verify() -> list[str]:
    expected: dict[str, str] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual_paths = {
        path.relative_to(ROOT).as_posix() for path in (ROOT / "raw").iterdir() if path.is_file()
    }
    failures: list[str] = []
    if actual_paths != set(expected):
        failures.append(
            f"raw file set changed: expected={sorted(expected)}, actual={sorted(actual_paths)}"
        )
    for relative_path, expected_hash in expected.items():
        path = ROOT / relative_path
        if not path.is_file():
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            failures.append(f"hash mismatch: {relative_path}")
    return failures


if __name__ == "__main__":
    errors = verify()
    if errors:
        raise SystemExit("\n".join(errors))
    print("raw integrity: PASS (3 files, SHA-256 byte-for-byte match)")
