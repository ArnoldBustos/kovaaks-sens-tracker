try:
  import numpy as np
  HAS_NUMPY = True
except ImportError:
  HAS_NUMPY = False


def calc_median(scores):
  if not scores:
    return None
  sorted_scores = sorted(scores)
  count = len(sorted_scores)
  midpoint = count // 2
  if count % 2:
    return sorted_scores[midpoint]
  return (sorted_scores[midpoint - 1] + sorted_scores[midpoint]) / 2


def estimate_best_cm(cm_best_scores: dict):
  points = [(cm, score) for cm, score in cm_best_scores.items() if score is not None]
  if len(points) < 2:
    return None, None

  points.sort()
  xs = [point[0] for point in points]
  ys = [point[1] for point in points]

  peak_index = ys.index(max(ys))
  raw_peak = xs[peak_index]

  if HAS_NUMPY and len(points) >= 3:
    try:
      coefficients = np.polyfit(xs, ys, 2)
      a_value, b_value, _ = coefficients
      if a_value < 0:
        vertex_x = -b_value / (2 * a_value)
        vertex_x = max(min(xs), min(max(xs), vertex_x))
        return round(vertex_x, 1), "curve fit"
    except Exception:
      pass

  return float(raw_peak), "peak of data"


def estimate_worst_cm(cm_best_scores: dict):
  points = [(cm, score) for cm, score in cm_best_scores.items() if score is not None]
  if len(points) < 2:
    return None, None

  points.sort()
  xs = [point[0] for point in points]
  ys = [point[1] for point in points]

  valley_index = ys.index(min(ys))
  raw_valley = xs[valley_index]

  if HAS_NUMPY and len(points) >= 3:
    try:
      coefficients = np.polyfit(xs, ys, 2)
      a_value, b_value, _ = coefficients
      if a_value > 0:
        vertex_x = -b_value / (2 * a_value)
        vertex_x = max(min(xs), min(max(xs), vertex_x))
        return round(vertex_x, 1), "curve fit"
    except Exception:
      pass

  return float(raw_valley), "valley of data"


def recommend_next_cm(cm_bests: dict, estimated_cm, all_cms_tested: list):
  if not cm_bests or len(cm_bests) < 2:
    return 40.0, "need at least 2 data points — start somewhere in the middle"

  tested_cms = sorted(cm_bests.keys())
  low_cm = tested_cms[0]
  high_cm = tested_cms[-1]

  if estimated_cm is not None and estimated_cm <= low_cm + 1:
    suggestion = max(1.0, low_cm - 10)
    return suggestion, f"peak is at/near left edge ({low_cm} cm) — test lower to find true peak"

  if estimated_cm is not None and estimated_cm >= high_cm - 1:
    suggestion = high_cm + 10
    return suggestion, f"peak is at/near right edge ({high_cm} cm) — test higher to find true peak"

  best_gap_value = -1
  best_suggestion = None
  best_reason = ""
  for index in range(len(tested_cms) - 1):
    left_cm = tested_cms[index]
    right_cm = tested_cms[index + 1]
    gap = right_cm - left_cm
    midpoint = (left_cm + right_cm) / 2
    proximity = 1.0
    if estimated_cm is not None:
      distance = abs(midpoint - estimated_cm)
      proximity = 1.0 + max(0, 1.0 - distance / 20.0)
    weighted_gap = gap * proximity
    if weighted_gap > best_gap_value:
      best_gap_value = weighted_gap
      best_suggestion = round(midpoint)
      best_reason = f"largest gap between {left_cm:.4g} and {right_cm:.4g} cm"

  if best_suggestion is not None:
    if any(abs(best_suggestion - tested_cm) < 2 for tested_cm in tested_cms):
      best_suggestion = round(best_suggestion + 1)
    return float(best_suggestion), best_reason

  return float((low_cm + high_cm) / 2), "fill midpoint of tested range"
