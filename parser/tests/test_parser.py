import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from parser import extract_python

def test_extract_python_single_block():
  text = textwrap.dedent("""
    Some intro
    ```python
    print("Hello World")
    ```
    Some conclusion
  """)
  result = extract_python(text)
  assert len(result) == 1
  assert result[0] == 'print("Hello World")'

def test_extract_python_multiple_blocks():
  text = textwrap.dedent("""
    ```python
    a = 1
    ```
    ```python
    b = 2
    ```
  """)
  result = extract_python(text)
  assert len(result) == 2
  assert result[0] == 'a = 1'
  assert result[1] == 'b = 2'

def test_extract_python_no_block():
  text = "Just some text without any code blocks"
  result = extract_python(text)
  assert len(result) == 0

def test_extract_python_malformed():
  text = "```python print(\"Unclosed tag\")"
  result = extract_python(text)
  assert len(result) == 0