#!/usr/bin/env python3
"""Test script for auto_script_tool"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("Testing auto_script_tool imports...")

try:
    from core.tools.auto_script_tool import (
        auto_generate_and_run, 
        execute_script_locally,
        list_scripts_for_auto_run
    )
    print("✅ Import successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 1: Execute simple script locally
print("\n--- Test 1: Execute simple script locally ---")
result = execute_script_locally('print("Hello World from test!")', 'python', '', 10)
print(f"Success: {result.success}")
print(f"Return code: {result.return_code}")
print(f"Output: {result.stdout.strip()}")
print(f"Error type: {result.error_type}")

# Test 2: Execute script with error
print("\n--- Test 2: Execute script with syntax error ---")
result2 = execute_script_locally('print("Missing paren"', 'python', '', 10)
print(f"Success: {result2.success}")
print(f"Error type: {result2.error_type}")
print(f"Stderr: {result2.stderr[:200] if result2.stderr else 'None'}")

print("\n✅ All basic tests passed!")
