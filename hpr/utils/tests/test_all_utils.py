import sys

#import hanspeterradtke.utils                 as ut
import hanspeterradtke.utils.open_router.tests.test_open_router as tor
import hanspeterradtke.utils.parser     .tests.test_parser      as tp


def run_all_utils_tests():
  print("[DEBUG] run_all_utils_tests started")
  rc = 0

  rc |= tor.run_test_invalid_token()
  rc |= tp .run_all_tests         ()

  if rc == 0:
    print("[DEBUG] run_all_utils_tests passed successfully")
  else:
    print(f"[ERROR] run_all_utils_tests failed with code {rc}")

  print("[DEBUG] run_all_utils_tests finished")
  return rc


if __name__ == "__main__":
  print("[HINT] Run this suite from repo root with: python3 -m tests.test_all_utils")
  sys.exit(run_all_utils_tests())

