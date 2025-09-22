# Parser Module

Extracts all Python code blocks from markdown-like text content. Mostly used to process OpenRouter LLM responses.

---

## Installation

This module is part of the `hpr-utils` package.

Install the full repo in editable mode (from repo root):

pip install -e .

---

## Functionality

### Python Function:
- `extract_python(text)`
  - Input: Any string
  - Output: List of strings, one per Python code block found between triple-backtick python tags (` ```python ... ``` `)

Used internally by the main script.

---

## CLI Usage

From the repo root, run:

python3 -m hpr.utils.parser

This will:
- Read the file `open_router/output.txt`
- Extract Python code blocks using `extract_python`
- Print them to stdout

---

## Files

- `__init__.py`: Core function `extract_python`
- `__main__.py`: Reads OpenRouter output and runs extract

---

## Tests

Run the full test suite from repo root:

python3 -m hpr.utils.parser.tests.test_parser

Covers:
- Single block
- Multiple blocks
- No blocks
- Malformed syntax

---

## Notes

- This module assumes OpenRouter’s output was saved in `output.txt`
- To use it standalone, modify `__main__.py` to use a different input file
