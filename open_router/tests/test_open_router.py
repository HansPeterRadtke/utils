import os
import sys
from pathlib import Path

# Ensure src is in Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'src'))

from utils.open_router.__main__ import main as run_open_router

def test_open_router_fake_output(monkeypatch):
  monkeypatch.setenv("LLM_TEST_MODE", "true")
  monkeypatch.setattr(sys, "argv", ["__main__.py"])

  base = Path(__file__).resolve().parents[4]
  router_dir = base / 'src' / 'utils' / 'open_router'

  prompt_file = router_dir / 'prompt.txt'
  output_file = router_dir / 'output.txt'

  prompt_file.write_text("Write a Hello World script in Python.")
  if output_file.exists():
    output_file.unlink()

  run_open_router()

  assert output_file.exists(), "Output file not created"
  content = output_file.read_text()
  assert "Hello world" in content or "print(" in content, "Fake output missing expected content"
  print("[DEBUG] Test OpenRouter test-mode response passed successfully!")