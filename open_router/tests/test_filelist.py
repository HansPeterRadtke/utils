import os
from pathlib import Path


def run_test_filelist():
    print("[DEBUG] run_test_filelist started")

    base = Path(__file__).resolve().parents[2]  # repo root: utils/
    router_dir = base / 'open_router'
    tests_dir = router_dir / 'tests'

    script1 = tests_dir / 'test_script_01.py'
    script2 = tests_dir / 'test_script_02.py'

    prompt_file = router_dir / 'prompt.txt'
    output_file = router_dir / 'output.txt'
    dump_file = router_dir / 'debug_prompt.txt'

    # Clean up before running
    if prompt_file.exists():
        prompt_file.unlink()
    if output_file.exists():
        output_file.unlink()
    if dump_file.exists():
        dump_file.unlink()

    cmd = (
        f"python3 -m open_router "
        f"--files {script1} {script2} "
        f"--prompt 'Please analyze the provided code files.' "
        f"--token ABC123 --debug_prompt --dump_prompt {dump_file}"
    )

    print(f"[DEBUG] Running command: {cmd}")
    rc = os.system(cmd)
    print(f"[DEBUG] os.system returned {rc}")

    if dump_file.exists():
        print("\n[DEBUG] Content of debug_prompt.txt:")
        with open(dump_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("[ERROR] debug_prompt.txt was not created")

    if prompt_file.exists():
        print("\n[DEBUG] Content of prompt.txt:")
        with open(prompt_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("[HINT] prompt.txt not created (not required, only read if no --prompt)")

    if output_file.exists():
        print("\n[DEBUG] Content of output.txt:")
        with open(output_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("[HINT] output.txt not created (invalid token, expected)")

    print("[DEBUG] run_test_filelist finished")
    return 0


if __name__ == "__main__":
    print("[HINT] Run this test from repo root with: python3 -m open_router.tests.test_filelist")
    run_test_filelist()