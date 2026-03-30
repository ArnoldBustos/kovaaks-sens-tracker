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

    tested_cms = sorted(float(cm) for cm in all_cms_tested)
    low_cm = tested_cms[0]
    high_cm = tested_cms[-1]

    def is_tested(candidate_cm, tolerance=0.15):
        for tested_cm in tested_cms:
            if abs(candidate_cm - tested_cm) <= tolerance:
                return True
        return False

    def nearest_untested_inside_gap(left_cm, right_cm):
        gap_midpoint = (left_cm + right_cm) / 2

        candidate_values = [
            round(gap_midpoint, 1),
            round((left_cm + gap_midpoint) / 2, 1),
            round((right_cm + gap_midpoint) / 2, 1),
            round(gap_midpoint - 0.2, 1),
            round(gap_midpoint + 0.2, 1),
        ]

        in_gap_candidates = []
        for candidate_cm in candidate_values:
            if left_cm < candidate_cm < right_cm and not is_tested(candidate_cm):
                in_gap_candidates.append(candidate_cm)

        if not in_gap_candidates:
            fallback_candidate = round(gap_midpoint, 2)
            if left_cm < fallback_candidate < right_cm and not is_tested(
                fallback_candidate, tolerance=0.05
            ):
                return fallback_candidate
            return None

        if estimated_cm is not None:
            return min(
                in_gap_candidates,
                key=lambda candidate_cm: abs(candidate_cm - estimated_cm),
            )

        return min(
            in_gap_candidates, key=lambda candidate_cm: abs(candidate_cm - gap_midpoint)
        )

    if estimated_cm is not None and estimated_cm <= low_cm + 0.75:
        suggestion = round(max(1.0, low_cm - 2.0), 1)
        if not is_tested(suggestion):
            return (
                suggestion,
                f"peak is near left edge ({low_cm:.4g} cm) — test a bit lower",
            )

    if estimated_cm is not None and estimated_cm >= high_cm - 0.75:
        suggestion = round(high_cm + 2.0, 1)
        if not is_tested(suggestion):
            return (
                suggestion,
                f"peak is near right edge ({high_cm:.4g} cm) — test a bit higher",
            )

    best_gap_score = None
    best_suggestion = None
    best_reason = None

    for index in range(len(tested_cms) - 1):
        left_cm = tested_cms[index]
        right_cm = tested_cms[index + 1]
        gap_width = right_cm - left_cm

        if gap_width < 0.3:
            continue

        gap_midpoint = (left_cm + right_cm) / 2
        proximity_bonus = 1.0
        if estimated_cm is not None:
            distance_from_estimate = abs(gap_midpoint - estimated_cm)
            proximity_bonus = max(0.25, 1.5 - (distance_from_estimate / 10.0))

        weighted_gap_score = gap_width * proximity_bonus
        candidate_cm = nearest_untested_inside_gap(left_cm, right_cm)

        if candidate_cm is None:
            continue

        if best_gap_score is None or weighted_gap_score > best_gap_score:
            best_gap_score = weighted_gap_score
            best_suggestion = candidate_cm
            best_reason = f"fill gap between {left_cm:.4g} and {right_cm:.4g} cm"

    if best_suggestion is not None:
        return best_suggestion, best_reason

    if estimated_cm is not None and not is_tested(round(estimated_cm, 1)):
        return round(estimated_cm, 1), "test nearest untested point to estimated peak"

    fallback_cm = round((low_cm + high_cm) / 2, 1)
    if not is_tested(fallback_cm):
        return fallback_cm, "fill midpoint of tested range"

    return round(high_cm + 1.0, 1), "expand search slightly"
