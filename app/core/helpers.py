# -------------------------
# HELPER FUNCTIONS
# -------------------------


def format_eta(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))

    if seconds < 60:
        return f"{seconds} sec"

    minutes, remaining_seconds = divmod(seconds, 60)

    if minutes < 60:
        if remaining_seconds == 0:
            return f"{minutes} min"
        return f"{minutes} min {remaining_seconds} sec"

    hours, remaining_minutes = divmod(minutes, 60)
    if remaining_minutes == 0:
        return f"{hours} hr"
    return f"{hours} hr {remaining_minutes} min"


def safe_percent(count: int, total: int) -> int:
    if total == 0:
        return 0
    return round((count / total) * 100)
