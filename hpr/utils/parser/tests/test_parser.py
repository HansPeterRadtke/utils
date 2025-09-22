import sys
import textwrap

from hanspeterradtke.utils.parser import extract_python


def run_test_extract_python_single_block():
  print("[DEBUG] run_test_extract_python_single_block started")
  text = textwrap.dedent("""
    Some intro
    ```python
    print("Hello World")
    ```
    Some conclusion
  """)
  result = extract_python(text)
  if not (len(result) == 1 and result[0] == 'print("Hello World")'):
    print("[ERROR] test_extract_python_single_block failed", result)
    return 1
  print("[DEBUG] run_test_extract_python_single_block passed")
  return 0


def run_test_extract_python_multiple_blocks():
  print("[DEBUG] run_test_extract_python_multiple_blocks started")
  text = textwrap.dedent("""
    ```python
    a = 1
    ```
    ```python
    b = 2
    ```
  """)
  result = extract_python(text)
  if not (len(result) == 2 and result[0] == 'a = 1' and result[1] == 'b = 2'):
    print("[ERROR] test_extract_python_multiple_blocks failed", result)
    return 1
  print("[DEBUG] run_test_extract_python_multiple_blocks passed")
  return 0


def run_test_extract_python_no_block():
  print("[DEBUG] run_test_extract_python_no_block started")
  text = "Just some text without any code blocks"
  result = extract_python(text)
  if len(result) != 0:
    print("[ERROR] test_extract_python_no_block failed", result)
    return 1
  print("[DEBUG] run_test_extract_python_no_block passed")
  return 0


def run_test_extract_python_malformed():
  print("[DEBUG] run_test_extract_python_malformed started")
  text = "```python print(\"Unclosed tag\")"
  result = extract_python(text)
  if len(result) != 0:
    print("[ERROR] test_extract_python_malformed failed", result)
    return 1
  print("[DEBUG] run_test_extract_python_malformed passed")
  return 0


def run_all_tests():
  rc = 0
  rc |= run_test_extract_python_single_block()
  rc |= run_test_extract_python_multiple_blocks()
  rc |= run_test_extract_python_no_block()
  rc |= run_test_extract_python_malformed()
  return rc


if __name__ == "__main__":
  print("[HINT] Run this test from repo root with: python3 -m parser.tests.test_parser")
  sys.exit(run_all_tests())
