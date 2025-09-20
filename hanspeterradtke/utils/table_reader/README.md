# Table Reader Module

A command-line utility to explore structured tabular data. Supports JSON list-of-dicts or pickled Pandas DataFrames.

---

## Installation

This module is part of the `hanspeterradtke-utils` package.

Install in editable mode (from repo root):

pip install -e .

---

## Input Formats

- `.json` files: Must be a list of dicts or a dict with key `data`
- `.pkl` files: Must be a pickled Pandas DataFrame

---

## CLI Usage

Run from anywhere:

python3 -m hanspeterradtke.utils.table_reader [file] [options]

Example:

python3 -m hanspeterradtke.utils.table_reader data.json --list-columns --head 5

---

## CLI Options

--list-columns: Show column names
--head N: Show first N rows
--tail N: Show last N rows
--slice start:end: Slice rows by position (e.g. 10:50)
--sort-by COLUMN: Sort by column
--descending: Sort in descending order
--filter col=val [col2=val2...]: Filter rows matching column=value
--contains COLUMN SUBSTRING: Filter rows where column contains substring
--unique COLUMN: Show all unique values of a column
--describe: Show DataFrame summary statistics
--dtypes: Show column data types

---

## Examples

Show summary:
python3 -m hanspeterradtke.utils.table_reader data.json --describe

Filter:
python3 -m hanspeterradtke.utils.table_reader data.json --filter status=active

Combined:
python3 -m hanspeterradtke.utils.table_reader data.json --filter type=error --sort-by timestamp --tail 10

---

## Files

- `__init__.py`: Contains all logic
- `__main__.py`: Entry point to call main()

---

## Notes

Output is limited to 50 rows by default using Pandas display options.
This module prints directly to stdout.
