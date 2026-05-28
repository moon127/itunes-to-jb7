VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip3

.PHONY: help setup run test coverage clean

help:
	@echo "Targets:"
	@echo "  setup      Create venv and install dependencies"
	@echo "  run        Launch the GUI application"
	@echo "  test       Run tests with pytest"
	@echo "  coverage   Run tests with coverage (requires >90%)"
	@echo "  clean      Remove venv and cached files"

setup: $(VENV)

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov

run: $(VENV)
	$(PYTHON) -m src.app

test: $(VENV)
	$(PYTHON) -m pytest tests/ -v

coverage: $(VENV)
	$(PYTHON) -m pytest tests/ --cov=src \
		--cov-report=term-missing --cov-fail-under=90 \
		--cov-report=html --cov-config=.coveragerc

clean:
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov
