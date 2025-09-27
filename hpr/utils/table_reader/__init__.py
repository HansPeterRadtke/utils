#!/usr/bin/env python3
import argparse
import json
import sys
import os
import pandas as pd


def load_data(path):
    if not os.path.exists(path):
        sys.exit(f"[ERROR] File not found: {path}")

    # Try JSON list of dicts
    if path.endswith(".json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            sys.exit(f"[ERROR] Failed to read JSON: {e}")

        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            records = data["data"]
        elif isinstance(data, list) and all(isinstance(x, dict) for x in data):
            records = data
        else:
            sys.exit("[ERROR] JSON file must be list of dicts or dict with key 'data'")

        # Flatten nested dicts into columns
        df = pd.json_normalize(records)

    # Try pickled Pandas DataFrame
    elif path.endswith(".pkl"):
        try:
            df = pd.read_pickle(path)
        except Exception as e:
            sys.exit(f"[ERROR] Failed to read DataFrame pickle: {e}")
        if not isinstance(df, pd.DataFrame):
            sys.exit("[ERROR] Pickle is not a Pandas DataFrame")
    else:
        sys.exit("[ERROR] Unsupported file type. Use .json (list of dicts) or .pkl (DataFrame).")

    # Try to convert string columns to numeric if possible
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            except Exception:
                pass

    return df


def main():
    p = argparse.ArgumentParser(description="Table Reader CLI: Explore list-of-dicts JSON or Pandas DataFrames")
    p.add_argument("file", help="Path to JSON or DataFrame pickle file")
    p.add_argument("--list-columns", action="store_true", help="List available columns")
    p.add_argument("--head", type=int, help="Show first N rows")
    p.add_argument("--tail", type=int, help="Show last N rows")
    p.add_argument("--slice", help="Slice rows, e.g. 20:100")
    p.add_argument("--sort-by", help="Column name to sort by")
    p.add_argument("--descending", action="store_true", help="Sort descending instead of ascending")
    p.add_argument("--filter", nargs="+", help="Filter rows, e.g. column=value")
    p.add_argument("--contains", nargs=2, metavar=("COLUMN", "SUBSTRING"), help="Filter rows where COLUMN contains SUBSTRING (case-insensitive)")
    p.add_argument("--unique", help="Show unique values of a column")
    p.add_argument("--describe", action="store_true", help="Show DataFrame describe() summary")
    p.add_argument("--dtypes", action="store_true", help="Show column data types")
    # NEW: select specific columns
    p.add_argument("--select", nargs="+", help="Select specific columns to display")

    args = p.parse_args()

    df = load_data(args.file)

    if args.list_columns:
        print("[INFO] Columns:", list(df.columns))

    if args.dtypes:
        print("[INFO] Column data types:")
        print(df.dtypes)

    if args.filter:
        for cond in args.filter:
            if "=" not in cond:
                sys.exit(f"[ERROR] Invalid filter format: {cond}, use column=value")
            col, val = cond.split("=", 1)
            if col not in df.columns:
                sys.exit(f"[ERROR] Column not found: {col}")
            df = df[df[col].astype(str) == val]

    if args.contains:
        col, substr = args.contains
        if col not in df.columns:
            sys.exit(f"[ERROR] Column not found: {col}")
        df = df[df[col].astype(str).str.contains(substr, case=False, na=False)]

    if args.sort_by:
        if args.sort_by not in df.columns:
            sys.exit(f"[ERROR] Column not found for sorting: {args.sort_by}")
        df = df.sort_values(by=args.sort_by, ascending=not args.descending)

    if args.slice:
        try:
            start, end = args.slice.split(":")
            start = int(start) if start else None
            end = int(end) if end else None
            df = df.iloc[start:end]
        except Exception as e:
            sys.exit(f"[ERROR] Invalid slice format: {args.slice}, use start:end")

    if args.head:
        df = df.head(args.head)

    if args.tail:
        df = df.tail(args.tail)

    if args.unique:
        if args.unique not in df.columns:
            sys.exit(f"[ERROR] Column not found: {args.unique}")
        uniques = df[args.unique].unique()
        print(f"[INFO] Unique values for column '{args.unique}' ({len(uniques)}):")
        for v in uniques:
            print("  ", v)

    if args.describe:
        print("[INFO] DataFrame describe():")
        print(df.describe(include="all"))

    # NEW: reduce to selected columns
    if args.select:
        for col in args.select:
            if col not in df.columns:
                sys.exit(f"[ERROR] Column not found in --select: {col}")
        df = df[args.select]

    # Print final result (full, not shortened)
    if not (args.unique or args.describe or args.list_columns or args.dtypes):
        try:
            with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.max_colwidth', None):
                print(df)
        except Exception as e:
            sys.exit(f"[ERROR] Could not display DataFrame: {e}")


if __name__ == "__main__":
    main()