import json

from .constants import DATA_FILE


def load_data():
  if DATA_FILE.exists():
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
        data.setdefault("assignments", {})
        data.setdefault("ranks", {})
        return data
    except Exception:
      pass
  return {"assignments": {}, "ranks": {}}


def save_data(data):
  try:
    with open(DATA_FILE, "w", encoding="utf-8") as file_handle:
      json.dump(data, file_handle, indent=2)
  except Exception as error:
    print(f"Save error: {error}")
