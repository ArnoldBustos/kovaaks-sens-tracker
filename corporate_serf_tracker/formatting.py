import re


def get_effective_cm(play, assignments):
    manual_cm = assignments.get(play["filename"])
    if manual_cm is not None:
        return float(manual_cm)
    
    auto_cm = play.get("cm360")
    if auto_cm is not None:
        return float(auto_cm)
    return None


def fmt_score(score):
    if score is None:
        return "—"
    return f"{round(score):,}"


def fmt_ts(timestamp):
    if not timestamp:
        return "—"
    match = re.match(r"(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})", timestamp)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}  {match.group(4)}:{match.group(5)}"
    return timestamp
