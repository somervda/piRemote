#!/usr/bin/env python3
"""
Read a .ir (IR signals) file and print each key name, one per line.

The .ir format (lirc-style) defines entries like:

    #
    name:D Audio
    type: raw
    frequency: 38000
    duty_cycle: 0.330000
    data: 2428 563 634 ...

Each key/button has a line beginning with "name:" followed by its value.
"""

import sys
import re
from pathlib import Path


def extract_names(filepath: str) -> list[str]:
    """Return a list of names found in the given .ir file."""
    names: list[str] = []
    # Match lines like:  name:Some Key  (colon may be followed by a space)
    name_re = re.compile(r'^\s*name\s*:\s*(.+?)\s*$')

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = name_re.match(line)
            if m:
                names.append(m.group(1).strip())
    return names


def main() -> None:
    filepath = sys.argv[1] if len(sys.argv) > 1 else "keys.ir"

    if not Path(filepath).exists():
        print(f"Error: '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)

    names = extract_names(filepath)

    if not names:
        print(f"No names found in '{filepath}'.", file=sys.stderr)
        sys.exit(1)

    for name in names:
        print(name)


if __name__ == "__main__":
    main()