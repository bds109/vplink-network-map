#!/usr/bin/env python3
"""csv-normalize-v1: deterministic UTF-8 CSV serialization, no value/row edits."""
import csv
import io
import sys

try:
    original = sys.stdin.buffer.read().decode('utf-8-sig', errors='strict')
    rows = list(csv.reader(io.StringIO(original, newline=''), strict=True))
    output = io.StringIO(newline='')
    csv.writer(output, lineterminator='\n', quoting=csv.QUOTE_MINIMAL).writerows(rows)
    sys.stdout.buffer.write(output.getvalue().encode('utf-8'))
except (UnicodeError, csv.Error):
    # Do not echo private source cells/filenames into CI or operator logs.
    sys.stderr.write('CSV normalization failed\n')
    sys.exit(1)
