"""Post-production quality checks that actually measure the output.

The production report used to print a fixed list of ✓ marks regardless of what
happened. These checks inspect the real lyrics timing and output files and
report genuine pass/fail results.
"""

from pathlib import Path


def _check(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail}


def run_quality_checks(lyrics_result, duration: float, output_files: dict) -> list:
    """Run measurable quality checks and return a list of result dicts.

    Args:
        lyrics_result: object with a ``.lines`` list of lyric lines, each having
            ``.start``, ``.end`` and ``.words``.
        duration: audio duration in seconds.
        output_files: mapping of label -> path (or None if skipped) for the
            expected deliverables.
    """
    checks = []
    lines = list(getattr(lyrics_result, "lines", []) or [])

    # 1. There are lyrics at all.
    checks.append(_check("Lyrics present", len(lines) > 0, f"{len(lines)} line(s)"))

    if lines:
        # 2. Nothing is timed past the end of the audio.
        max_end = max(l.end for l in lines)
        checks.append(_check(
            "Lyrics within audio duration",
            max_end <= duration + 0.5,
            f"last line ends at {max_end:.1f}s / {duration:.1f}s",
        ))

        # 3. Lines are in chronological order.
        starts = [l.start for l in lines]
        monotonic = all(b >= a - 0.01 for a, b in zip(starts, starts[1:]))
        checks.append(_check(
            "Lyric lines in chronological order",
            monotonic,
            "start times non-decreasing" if monotonic else "found out-of-order lines",
        ))

        # 4. Every line has a positive on-screen duration.
        positive = all(l.end > l.start for l in lines)
        checks.append(_check(
            "Positive line durations",
            positive,
            "all lines have end > start" if positive else "found zero/negative durations",
        ))

        # 5. How many lines carry real word-by-word timing.
        with_words = sum(1 for l in lines if l.words and len(l.words) > 1)
        frac = with_words / len(lines)
        checks.append(_check(
            "Word-level sync coverage",
            frac >= 0.5,
            f"{with_words}/{len(lines)} lines ({frac * 100:.0f}%)",
        ))

    # 6. Each expected deliverable exists and is non-empty.
    for label, path in (output_files or {}).items():
        if path is None:
            checks.append(_check(f"Output: {label}", True, "skipped"))
            continue
        p = Path(path)
        exists = p.exists() and p.stat().st_size > 0
        if exists:
            detail = f"{p.name} ({p.stat().st_size // 1024} KB)"
        else:
            detail = f"{p.name} missing or empty"
        checks.append(_check(f"Output: {label}", exists, detail))

    return checks


def summarize(checks: list) -> tuple:
    """Return (passed_count, total_count)."""
    passed = sum(1 for c in checks if c["passed"])
    return passed, len(checks)
