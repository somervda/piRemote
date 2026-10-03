#!/usr/bin/env python3
"""
Read the file `Yamaha.ir` and write a new file `yamahashort.ir`.
All lines are copied verbatim, except that for lines that start with
`data:` we keep only the first 41 comma‑separated timing values.
"""

INPUT_FILE   = "Yamaha.ir"
OUTPUT_FILE  = "yamahashort.ir"
DATA_PREFIX  = "data:"          # line prefix to look for
MAX_VALUES   = 41               # how many timing values to keep

def process_data_line(line: str) -> str:
    """
    Keep only the first MAX_VALUES values after the prefix.
    The original line format is assumed to be:
        data: 1 2 3 4 5 ...
    """
    # Remove the prefix and any leading/trailing whitespace
    values_part = line[len(DATA_PREFIX):].strip()

    # Split on whitespace (works for spaces or tabs)
    values = values_part.split()

    # Truncate to the desired number of values
    limited = values[:MAX_VALUES]

    # Re‑assemble the line
    return DATA_PREFIX + " " + " ".join(limited) + "\n"

def main() -> None:
    with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as fout:

        for raw_line in fin:
            # Detect lines that start with the exact prefix
            if raw_line.startswith(DATA_PREFIX):
                fout.write(process_data_line(raw_line))
            else:
                fout.write(raw_line)

    print(f"Finished writing {OUTPUT_FILE}")

if __name__ == "__main__":
    main()