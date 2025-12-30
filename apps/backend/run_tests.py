#!/usr/bin/env python3
"""
Test runner script for the backend application
Provides convenient ways to run different types of tests
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def run_all_tests(verbose=False, coverage=False, parallel=False):
    """Run all tests with specified options"""
    cmd = ["python", "-m", "pytest", "tests/"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml"
        ])

    if parallel:
        cmd.extend(["-n", "auto"])

    return run_command(cmd)


def run_unit_tests():
    """Run only unit tests"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "unit", "-v"]
    return run_command(cmd)


def run_integration_tests():
    """Run only integration tests"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "integration", "-v"]
    return run_command(cmd)


def run_auth_tests():
    """Run authentication tests"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "auth", "-v"]
    return run_command(cmd)


def run_trading_tests():
    """Run trading system tests"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "trading", "-v"]
    return run_command(cmd)


def run_price_tests():
    """Run price data tests"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "price", "-v"]
    return run_command(cmd)


def run_database_tests():
    """Run database tests"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "database", "-v"]
    return run_command(cmd)


def run_slow_tests():
    """Run slow tests"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "slow", "-v"]
    return run_command(cmd)


def run_coverage_report():
    """Generate coverage report"""
    cmd = [
        "python", "-m", "pytest", "tests/",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml",
        "--cov-fail-under=80"
    ]
    return run_command(cmd)


def run_specific_test(test_path):
    """Run a specific test file or test function"""
    cmd = ["python", "-m", "pytest", test_path, "-v"]
    return run_command(cmd)


def install_test_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    cmd = ["pip", "install", "-r", "test-requirements.txt"]
    return run_command(cmd)


def clean_test_artifacts():
    """Clean up test artifacts"""
    print("Cleaning up test artifacts...")

    # Remove test database
    if os.path.exists("test.db"):
        os.remove("test.db")
        print("Removed test.db")

    # Remove coverage files
    coverage_files = [".coverage", "htmlcov/", "coverage.xml"]
    for artifact in coverage_files:
        if os.path.exists(artifact):
            if os.path.isdir(artifact):
                import shutil
                shutil.rmtree(artifact)
                print(f"Removed directory: {artifact}")
            else:
                os.remove(artifact)
                print(f"Removed file: {artifact}")

    # Remove pytest cache
    if os.path.exists(".pytest_cache/"):
        import shutil
        shutil.rmtree(".pytest_cache/")
        print("Removed .pytest_cache/")


def check_test_setup():
    """Check if test environment is properly set up"""
    print("Checking test environment...")

    # Check if pytest is installed
    try:
        import pytest
        print(f"✅ pytest version: {pytest.__version__}")
    except ImportError:
        print("❌ pytest is not installed")
        return False

    # Check if test directory exists
    if os.path.exists("tests/"):
        print("✅ tests/ directory exists")
    else:
        print("❌ tests/ directory not found")
        return False

    # Check if test requirements exist
    if os.path.exists("test-requirements.txt"):
        print("✅ test-requirements.txt exists")
    else:
        print("❌ test-requirements.txt not found")
        return False

    # Check if source directory exists
    if os.path.exists("src/"):
        print("✅ src/ directory exists")
    else:
        print("❌ src/ directory not found")
        return False

    print("✅ Test environment looks good!")
    return True


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Test runner for backend application")
    parser.add_argument("command", nargs="?", default="all",
                       help="Test command to run (all, unit, integration, auth, trading, price, database, slow, coverage, clean, setup)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    parser.add_argument("--parallel", "-p", action="store_true", help="Run tests in parallel")
    parser.add_argument("--file", "-f", help="Run specific test file")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")

    args = parser.parse_args()

    # Change to the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Install dependencies if requested
    if args.install:
        return install_test_dependencies()

    # Check setup first
    if not check_test_setup():
        print("❌ Test environment is not properly set up")
        return 1

    # Run specific command
    if args.command == "all":
        return run_all_tests(args.verbose, args.coverage, args.parallel)
    elif args.command == "unit":
        return run_unit_tests()
    elif args.command == "integration":
        return run_integration_tests()
    elif args.command == "auth":
        return run_auth_tests()
    elif args.command == "trading":
        return run_trading_tests()
    elif args.command == "price":
        return run_price_tests()
    elif args.command == "database":
        return run_database_tests()
    elif args.command == "slow":
        return run_slow_tests()
    elif args.command == "coverage":
        return run_coverage_report()
    elif args.command == "clean":
        clean_test_artifacts()
        return 0
    elif args.command == "setup":
        return check_test_setup()
    elif args.file:
        return run_specific_test(args.file)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
