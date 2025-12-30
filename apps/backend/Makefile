.PHONY: help test test-unit test-integration test-auth test-trading test-price test-database test-slow test-coverage test-clean test-setup install-deps lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-auth     - Run authentication tests"
	@echo "  test-trading  - Run trading system tests"
	@echo "  test-price    - Run price data tests"
	@echo "  test-database - Run database tests"
	@echo "  test-slow     - Run slow tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-clean    - Clean test artifacts"
	@echo "  test-setup    - Check test setup"
	@echo "  install-deps  - Install test dependencies"
	@echo "  lint          - Run linting"
	@echo "  format        - Format code"

# Test commands
test:
	python run_tests.py all

test-verbose:
	python run_tests.py all --verbose

test-parallel:
	python run_tests.py all --parallel

test-unit:
	python run_tests.py unit

test-integration:
	python run_tests.py integration

test-auth:
	python run_tests.py auth

test-trading:
	python run_tests.py trading

test-price:
	python run_tests.py price

test-database:
	python run_tests.py database

test-slow:
	python run_tests.py slow

test-coverage:
	python run_tests.py coverage

test-clean:
	python run_tests.py clean

test-setup:
	python run_tests.py setup

install-deps:
	python run_tests.py --install

# Development commands
install-all:
	pip install -r requirement.txt
	pip install -r test-requirements.txt

lint:
	@echo "Running linting..."
	@echo "Note: Install flake8, black, isort for full linting support"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503; \
	else \
		echo "flake8 not installed. Install with: pip install flake8"; \
	fi

format:
	@echo "Formatting code..."
	@echo "Note: Install black, isort for code formatting"
	@if command -v black >/dev/null 2>&1; then \
		black src/ tests/ --line-length=100; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort src/ tests/ --profile black; \
	else \
		echo "isort not installed. Install with: pip install isort"; \
	fi

# CI commands
ci-test:
	python run_tests.py all --coverage --parallel

ci-setup:
	python run_tests.py setup
	python run_tests.py --install

# Development workflow
dev-setup: install-all test-setup
	@echo "Development environment setup complete!"

quick-test: test-unit
	@echo "Quick unit tests completed!"

full-test: test-clean test-coverage
	@echo "Full test suite with coverage completed!"

# Watch mode (requires pytest-watch)
watch:
	@if command -v ptw >/dev/null 2>&1; then \
		ptw tests/ --runner "python -m pytest" -v; \
	else \
		echo "pytest-watch not installed. Install with: pip install pytest-watch"; \
	fi

# Specific test file
test-file:
	@read -p "Enter test file path (e.g., tests/test_auth_endpoints.py): " file; \
	python run_tests.py --file $$file

# Debug test
debug:
	@read -p "Enter test function (e.g., tests/test_auth_endpoints.py::TestAuthEndpoints::test_register_user): " test; \
	python -m pytest $$test -v -s --tb=long

# Performance test
perf-test:
	python -m pytest tests/ -m "slow" -v --durations=10

# Generate HTML coverage report
html-coverage: test-coverage
	@echo "Coverage report generated in htmlcov/index.html"
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	fi
