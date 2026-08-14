"""Fast portfolio/release invariants that do not require AWS credentials."""

from __future__ import annotations

import re
from pathlib import Path

from verify_raw import verify

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = [
    "README.md",
    "resposta.md",
    "pyproject.toml",
    "Makefile",
    ".env.example",
    "apps/web/package.json",
    "infra/cdk/package.json",
    "docs/architecture.md",
    "docs/security.md",
    "docs/threat-model.md",
    "docs/cost-model.md",
    "docs/rag-evaluation.md",
    ".github/workflows/ci.yml",
]
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"aws_secret_access_key\s*=\s*[^\s<]+", re.IGNORECASE),
]


def main() -> None:
    failures = [
        f"missing required path: {path}" for path in REQUIRED_PATHS if not (ROOT / path).exists()
    ]
    resposta = (ROOT / "resposta.md").read_text(encoding="utf-8")
    if "Preencha aqui" in resposta:
        failures.append("resposta.md still contains 'Preencha aqui'")
    failures.extend(verify())
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(
            part
            in {
                ".git",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                ".venv",
                "node_modules",
                "build",
                "cdk.out",
                "tmp",
            }
            for part in path.parts
        ):
            continue
        if path.suffix.lower() in {".png", ".pdf", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                failures.append(f"possible credential in {path.relative_to(ROOT)}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("repository validation: PASS")


if __name__ == "__main__":
    main()
