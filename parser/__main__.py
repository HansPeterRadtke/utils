import os
from . import extract_python

def main():
  print("[DEBUG] __main__.py parser.main() started")
  try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    open_router_path = os.path.abspath(os.path.join(script_dir, '..', 'open_router', 'output.txt'))
    print(f"[DEBUG] Reading output from: {open_router_path}")
    with open(open_router_path, 'r', encoding='utf-8') as f:
      content = f.read()
    result = extract_python(content)
    print(f"[DEBUG] Extracted blocks: {result}")
  except Exception as e:
    print(f"[ERROR] Failed to read or extract: {e}")
  print("[DEBUG] __main__.py parser.main() finished")

if __name__ == '__main__':
  main()