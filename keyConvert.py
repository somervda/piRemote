#!/usr/bin/env python3
"""
keys_convert.py

Reads `keys.ir`, writes the transformed lines to `keys1.ir`.

Transformation rules for lines that start with "name:":

1. If the value starts with an uppercase “D” followed by letters,
   change it to:  "D " + <letters in title case>.
   Example:  "name: Dright"   ->  "name: D Right"

2. If the value does NOT start with an uppercase “D”,
   change it to:  "T " + <value in title case>.
   Example:  "name: 4"   ->  "name: T 4"
   Example:  "name: dleft" -> "name: T Dleft"
"""

import re
import sys

INPUT_FILE  = "keys.ir"
OUTPUT_FILE = "keys1.ir"

def transform_name(value: str) -> str:
    """Apply the name transformation rules."""
    # Strip any surrounding whitespace
    value = value.strip()

    # Rule 1: starts with an uppercase D followed by letters
    if re.match(r"^D[A-Za-z]+$", value):
        # Title‑case the trailing letters
        new_suffix = value[1:].title()
        return f"D {new_suffix}"

    # Rule 2: everything else
    return f"T {value.title()}"


def main() -> None:
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
             open(OUTPUT_FILE, "w", encoding="utf-8") as fout:

            for line in fin:
                # Check for lines that start with "name:" (ignoring leading spaces)
                if line.lstrip().startswith("name:"):
                    # Split into the prefix and the original value
                    prefix, _, rest = line.partition(":")
                    # The part after the colon may contain the value and a newline
                    original_value, _, newline = rest.partition("\n")
                    # Apply the transformation
                    new_value = transform_name(original_value)
                    # Re‑construct the line
                    new_line = f"{prefix}:{new_value}{newline}" + "\n"
                else:
                    # Non‑name lines are copied verbatim
                    new_line = line

                fout.write(new_line)

        print(f"Transformation complete: {OUTPUT_FILE}")

    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()