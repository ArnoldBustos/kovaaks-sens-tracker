import re
from collections import defaultdict
from pathlib import Path


def parse_filename(filename):
  stem = filename.replace(" Stats.csv", "")
  match = re.match(r"^(.+?)\s+-\s+(?:Challenge\s+-\s+)?(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})$", stem)
  if match:
    return match.group(1).strip(), match.group(2)

  parts = stem.split(" - ")
  if len(parts) >= 2:
    timestamp = parts[-1]
    scenario_name = " - ".join(parts[:-1]).removesuffix(" - Challenge").strip()
    return scenario_name, timestamp

  return None, None


def parse_stats_from_csv(filepath):
  try:
    with open(filepath, "r", encoding="utf-8", errors="replace") as file_handle:
      lines = file_handle.readlines()
  except Exception:
    return None, None, None, None

  score = None
  horizontal_sensitivity = None
  sensitivity_scale = None
  crosshair_name = None
  crosshair_scale = None

  for raw_line in lines:
    line = raw_line.strip()
    if not line:
      continue

    parts = line.split(",", 1)
    if len(parts) != 2:
      continue

    key = parts[0].strip().rstrip(":").lower()
    value = parts[1].strip()

    if key == "score":
      try:
        score = float(value)
      except ValueError:
        pass
    elif key == "horiz sens":
      try:
        horizontal_sensitivity = float(value)
      except ValueError:
        pass
    elif key == "sens scale":
      sensitivity_scale = value.strip().lower()
    elif key == "crosshair":
      crosshair_name = value or None
    elif key == "crosshair scale":
      try:
        crosshair_scale = float(value)
      except ValueError:
        crosshair_scale = value or None

  cm360 = None
  if horizontal_sensitivity is not None and sensitivity_scale == "cm/360":
    cm360 = horizontal_sensitivity

  return score, cm360, crosshair_name, crosshair_scale


def parse_score_from_csv(filepath):
  score, _, _, _ = parse_stats_from_csv(filepath)
  return score


def load_folder(folder_path):
  scenarios = defaultdict(list)
  folder = Path(folder_path)
  if not folder.exists():
    return {}

  for file_path in folder.iterdir():
    if not file_path.name.endswith("Stats.csv"):
      continue

    scenario_name, timestamp = parse_filename(file_path.name)
    if not scenario_name:
      continue

    score, cm360, crosshair_name, crosshair_scale = parse_stats_from_csv(file_path)
    if score is None:
      continue

    scenarios[scenario_name].append({
      "score": score,
      "ts": timestamp,
      "filename": file_path.name,
      "cm360": cm360,
      "crosshair_name": crosshair_name,
      "crosshair_scale": crosshair_scale,
    })

  for scenario_name in scenarios:
    scenarios[scenario_name].sort(key=lambda play: play["ts"] or "")

  return dict(scenarios)
