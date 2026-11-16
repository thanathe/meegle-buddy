#!/usr/bin/env python3
"""Print epoch milliseconds for Bangkok-time clock readings on one date.

Usage:  python3 bkk_ms.py YYYY-MM-DD HH:MM [HH:MM ...]
Prints one value per time, space-separated, in the order given.
Example: python3 bkk_ms.py 2026-05-31 09:00 10:30
"""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Bangkok")


def to_ms(date_str: str, hhmm: str) -> int:
    hour, minute = map(int, hhmm.split(":"))
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour, minute=minute, tzinfo=TZ)
    return int(dt.timestamp() * 1000)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    date_str, times = argv[0], argv[1:]
    try:
        print(" ".join(str(to_ms(date_str, t)) for t in times))
    except ValueError as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
