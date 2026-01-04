#!/usr/bin/env python3
"""Test truncated script detection"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.script_validator import is_script_truncated

# Test 1: Truncated script ending with "parser."
test1 = """
def main():
    parser = argparse.ArgumentParser()
    parser.
"""
r1, i1 = is_script_truncated(test1)
print(f"Test 1 (ends with 'parser.'): truncated={r1}, info='{i1}'")

# Test 2: Complete script
test2 = """
def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
r2, i2 = is_script_truncated(test2)
print(f"Test 2 (complete script): truncated={r2}")

# Test 3: Unbalanced parentheses
test3 = """
def test(
    arg1,
    arg2
"""
r3, i3 = is_script_truncated(test3)
print(f"Test 3 (unbalanced parens): truncated={r3}, info='{i3}'")

# Test 4: Has argparse but no main
test4 = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-u', '--url')
"""
r4, i4 = is_script_truncated(test4)
print(f"Test 4 (argparse, no main): truncated={r4}, info='{i4}'")

print("\nAll tests completed!")
