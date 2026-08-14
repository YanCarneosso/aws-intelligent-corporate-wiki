PYTHON ?= python3
PNPM ?= pnpm

.PHONY: install lint typecheck test build build-backend build-frontend synth smoke verify verify-raw clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"
	$(PNPM) install --frozen-lockfile

lint:
	$(PYTHON) -m ruff check services shared tests scripts
	$(PYTHON) -m ruff format --check services shared tests scripts
	$(PNPM) -r lint

typecheck:
	$(PYTHON) -m mypy services shared scripts
	$(PNPM) --filter @wiki/web exec tsc -b
	$(PNPM) --filter @wiki/infrastructure build

test:
	$(PYTHON) -m pytest --cov --cov-report=term-missing --cov-report=xml
	$(PNPM) -r test

build-backend:
	$(PYTHON) scripts/package_lambda.py

build-frontend:
	$(PNPM) --filter @wiki/web build

build: build-backend build-frontend

synth: build
	$(PNPM) --filter @wiki/infrastructure synth

smoke:
	$(PYTHON) scripts/smoke_test.py

verify-raw:
	$(PYTHON) scripts/verify_raw.py

verify: lint typecheck test smoke verify-raw synth
	$(PYTHON) scripts/validate_repository.py
	git diff --check
	git diff --exit-code -- raw/

clean:
	$(PYTHON) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['build','cdk.out','apps/web/dist','infra/cdk/cdk.out']]"
