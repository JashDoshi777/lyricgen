"""
LRC format parser.
Converts raw LRC timestamps into structured JSON.
"""

import re


def parse_lrc(lrc_text):
    """
    Parse LRC formatted lyrics into a list of timed lines.

    Input format:
        [00:12.40] I said ooh
        [00:14.00] I'm blinded by the lights

    Output format:
        [
            {"time": 12.40, "text": "I said ooh"},
            {"time": 14.00, "text": "I'm blinded by the lights"}
        ]

    Args:
        lrc_text: Raw LRC string.

    Returns:
        list: List of {time, text} dicts, sorted by time.
    """
    if not lrc_text:
        return []

    lines = []
    # Match patterns like [MM:SS.xx] or [MM:SS.xxx] or [MM:SS]
    pattern = re.compile(r'\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]\s*(.*)')

    for raw_line in lrc_text.strip().split('\n'):
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        # Some LRC files have multiple timestamps per line
        timestamps = re.findall(r'\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]', raw_line)
        text_match = re.search(r'\]\s*(.+)$', raw_line)
        text = text_match.group(1).strip() if text_match else ''

        if not text or not timestamps:
            continue

        for minutes, seconds, milliseconds in timestamps:
            ms = milliseconds or '0'
            # Normalize milliseconds (could be 2 or 3 digits)
            if len(ms) == 2:
                ms = int(ms) * 10
            else:
                ms = int(ms)

            time_sec = int(minutes) * 60 + int(seconds) + ms / 1000.0
            lines.append({
                'time': round(time_sec, 3),
                'text': text
            })

    # Sort by time
    lines.sort(key=lambda x: x['time'])
    return lines


def parse_plain_lyrics(text):
    """
    Convert plain text lyrics (no timestamps) into a list of lines.
    Assigns approximate timestamps (3 seconds per line).

    Args:
        text: Plain lyrics text.

    Returns:
        list: List of {time, text} dicts.
    """
    if not text:
        return []

    lines = []
    for i, line in enumerate(text.strip().split('\n')):
        line = line.strip()
        if line:
            lines.append({
                'time': i * 3.0,
                'text': line
            })

    return lines


def format_time(seconds):
    """Format seconds into MM:SS.xx string."""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:05.2f}"
