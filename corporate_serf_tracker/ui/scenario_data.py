from collections import defaultdict

from corporate_serf_tracker.analysis import (
    calc_median,
    estimate_best_cm,
    estimate_worst_cm,
    recommend_next_cm,
)
from corporate_serf_tracker.formatting import get_effective_cm


def build_cm_score_map(
    plays: list,
    assignments: dict,
    last_8_only: bool = False,
    cm_min: float | None = None,
    cm_max: float | None = None,
) -> dict:
    by_cm = defaultdict(list)

    for play in plays:
        cm_value = get_effective_cm(play, assignments)
        if cm_value is None:
            continue

        if cm_min is not None and cm_value < cm_min:
            continue

        if cm_max is not None and cm_value > cm_max:
            continue

        score_value = play.get("score")
        if score_value is None:
            continue

        by_cm[cm_value].append(score_value)

    sorted_cm_values = sorted(by_cm.keys())

    filtered_by_cm = {}
    for cm_value in sorted_cm_values:
        scores = by_cm[cm_value]
        if last_8_only:
            filtered_by_cm[cm_value] = scores[-8:]
        else:
            filtered_by_cm[cm_value] = scores

    return filtered_by_cm


def build_playable_entries(
    plays: list,
    assignments: dict,
    cm_min: float | None = None,
    cm_max: float | None = None,
) -> list:
    playable_entries = []

    for play in plays:
        cm_value = get_effective_cm(play, assignments)
        if cm_value is None:
            continue

        if cm_min is not None and cm_value < cm_min:
            continue

        if cm_max is not None and cm_value > cm_max:
            continue

        score_value = play.get("score")
        if score_value is None:
            continue

        playable_entries.append((play, cm_value, score_value))

    return playable_entries


def build_summary_stats(
    plays: list,
    assignments: dict,
    last_8_only: bool = False,
    cm_min: float | None = None,
    cm_max: float | None = None,
) -> dict:
    playable_entries = build_playable_entries(
        plays=plays,
        assignments=assignments,
        cm_min=cm_min,
        cm_max=cm_max,
    )

    by_cm_scores = build_cm_score_map(
        plays=plays,
        assignments=assignments,
        last_8_only=last_8_only,
        cm_min=cm_min,
        cm_max=cm_max,
    )

    all_scores = []
    for cm_value in sorted(by_cm_scores.keys()):
        for score_value in by_cm_scores[cm_value]:
            if score_value > 0:
                all_scores.append(score_value)

    best_score = None
    best_play = None
    best_cm = None

    if all_scores:
        best_score = max(all_scores)

        for play, cm_value, score_value in playable_entries:
            if score_value == best_score:
                best_play = play
                best_cm = cm_value
                break

    median_score = calc_median(all_scores)

    best_crosshair_label = "—"
    if best_play:
        crosshair_name = best_play.get("crosshair_name")
        crosshair_scale = best_play.get("crosshair_scale")

        if crosshair_name:
            if crosshair_scale is not None:
                best_crosshair_label = f"{crosshair_name} ({crosshair_scale})"
            else:
                best_crosshair_label = crosshair_name

    cm_best_scores = {}
    for cm_value, scores in by_cm_scores.items():
        if scores:
            cm_best_scores[cm_value] = max(scores)

    estimated_best_cm, estimated_best_method = estimate_best_cm(cm_best_scores)
    estimated_worst_cm, estimated_worst_method = estimate_worst_cm(cm_best_scores)
    next_cm, next_reason = recommend_next_cm(
        cm_best_scores,
        estimated_best_cm,
        list(cm_best_scores.keys()),
    )

    estimated_best_label = "Need more data"
    if estimated_best_cm is not None:
        estimated_best_label = f"~{estimated_best_cm} cm ({estimated_best_method})"

    worst_cm_label = "Need more data"
    if estimated_worst_cm is not None:
        worst_cm_label = f"~{estimated_worst_cm} cm ({estimated_worst_method})"

    next_cm_label = f"{next_cm:.4g} cm"
    if next_reason:
        next_cm_label = f"{next_cm:.4g} cm ({next_reason})"

    cm_for_best_label = "—"
    if best_cm is not None:
        cm_for_best_label = f"{best_cm} cm"

    filtered_play_count = 0
    for scores in by_cm_scores.values():
        filtered_play_count += len(scores)

    return {
        "best_score": best_score,
        "cm_for_best_label": cm_for_best_label,
        "best_crosshair_label": best_crosshair_label,
        "median_score": median_score,
        "total_plays": filtered_play_count,
        "estimated_best_label": estimated_best_label,
        "worst_cm_label": worst_cm_label,
        "next_cm_label": next_cm_label,
        "by_cm_scores": by_cm_scores,
    }


def parse_optional_float(raw_value: str) -> float | None:
    normalized_value = (raw_value or "").strip()
    if not normalized_value:
        return None

    try:
        return float(normalized_value)
    except ValueError:
        return None
