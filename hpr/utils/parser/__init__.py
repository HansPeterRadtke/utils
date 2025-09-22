import re

def extract_python(content):
  print("[DEBUG] extract_python started")
  try:
    matches = re.findall(r'```python(.*?)```', content, re.DOTALL)
    cleaned = [m.strip() for m in matches]
    print(f"[DEBUG] Found {len(cleaned)} Python blocks")
    print("[DEBUG] extract_python finished")
    return cleaned
  except Exception as e:
    print(f"[ERROR] Exception in extract_python: {e}")
    return []