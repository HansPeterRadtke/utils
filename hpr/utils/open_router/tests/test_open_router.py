import os
import sys
from pathlib import Path

from hpr.utils.open_router import __main__ as open_router


def run_test_invalid_token():
  print("[DEBUG] run_test_invalid_token started")

  # Do not touch global environment, just pass fake token as CLI arg
  sys.argv = ["__main__.py", "--prompt", "Say hello!", "--token", "ABC123"]

  base = Path(__file__).resolve().parents[2]  # repo root: utils/
  router_dir = base / 'open_router'
  output_file = router_dir / 'output.txt'
  if output_file.exists():
    output_file.unlink()

  try:
    open_router.main()
    print("[ERROR] Expected SystemExit but main() returned normally")
    return 1
  except SystemExit as e:
    print(f"[DEBUG] SystemExit caught as expected: {e}")

  if output_file.exists():
    print("[ERROR] Output file was created unexpectedly")
    return 2

  print("[DEBUG] run_test_invalid_token passed successfully")
  return 0


if __name__ == "__main__":
  print("[HINT] Run this test from repo root with: python3 -m open_router.tests.test_open_router")
  rc = run_test_invalid_token()
  sys.exit(rc)
