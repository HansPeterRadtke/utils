import os
import argparse
from . import extract_python

def main():
  print("[DEBUG] parser.main() started")

  parser = argparse.ArgumentParser(description="Extract Python code blocks from a file.")
  parser.add_argument('--from', dest='input_path', type=str, required=True, help='Path to input file')
  parser.add_argument('--to', dest='output_path', type=str, required=False, help='Path to output file')

  args = parser.parse_args()

  try:
    print(f"[DEBUG] Reading input from: {args.input_path}")
    with open(args.input_path, 'r', encoding='utf-8') as f:
      content = f.read()

    result = extract_python(content)

    if args.output_path:
      print(f"[DEBUG] Writing output to: {args.output_path}")
      with open(args.output_path, 'w', encoding='utf-8') as f:
        for block in result:
          f.write(block + '\n\n')
    else:
      print("[DEBUG] Extracted blocks:")
      for block in result:
        print(block)

  except Exception as e:
    print(f"[ERROR] Exception during processing: {e}")

  print("[DEBUG] parser.main() finished")

if __name__ == '__main__':
  main()