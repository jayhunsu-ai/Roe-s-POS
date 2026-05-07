#!/usr/bin/env python3
"""
Test Runner for POS System Backend
"""

import os
import sys
import subprocess

def run_tests():
    """Run all Django tests"""
    os.chdir("c:\\Users\\DELL\\Desktop\\Roe's POS\\Server\\backend")

    print("Running Django tests...")
    print("=" * 50)

    # Run tests with coverage
    try:
        result = subprocess.run([
            sys.executable, "manage.py", "test",
            "--verbosity=2",
            "--keepdb"  # Keep test database for faster runs
        ], capture_output=True, text=True, timeout=300)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print("=" * 50)
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("❌ Tests timed out!")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)