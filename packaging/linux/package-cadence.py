from __future__ import annotations

import re
import sys


def should_build_periodic(tag: str) -> bool:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", tag.strip())
    if not match:
        return False
    minor = int(match.group(2))
    return minor % 2 == 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    tag = args[0] if args else ""
    value = "true" if should_build_periodic(tag) else "false"
    print(f"build_periodic={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
