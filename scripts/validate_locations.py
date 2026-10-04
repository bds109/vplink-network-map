"""Read-only pre-release validation for the map's runtime CSV (standard library only)."""

import argparse
import ast
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "VPL门店地图信息.csv"
BRAND_CONFIG = ROOT / "scripts" / "brand_config.json"
MAP_TEMPLATE = ROOT / "scripts" / "map_template.html"
CORE_COLUMNS = {"ID", "StoreName", "StoreType", "State", "Latitude", "Longitude"}
OPTIONAL_COLUMNS = ("Address", "City", "PostalCode")
ID_PATTERN = re.compile(r"[1-9][0-9]*\Z")
BRAND_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
RESERVED_BRAND_SLUGS = {
    "network-overview", "preview", "data", "scripts", "docs", "photos",
    "handoff", "output", "backups", "rollback",
}
MAP_ENTRY = re.compile(r"\s*('(?:\\.|[^'\\])*')\s*:\s*('(?:\\.|[^'\\])*')\s*,?\s*\Z")


def state_mapping(template=MAP_TEMPLATE):
    source = Path(template).read_text(encoding="utf-8")
    blocks = re.findall(r"\bvar\s+stateNameMap\s*=\s*\{(.*?)\};", source, re.S)
    if len(blocks) != 1:
        raise ValueError("Expected exactly one stateNameMap in the current map template")
    mapping = {}
    for line in blocks[0].splitlines():
        if not line.strip():
            continue
        match = MAP_ENTRY.fullmatch(line)
        if not match:
            raise ValueError("Unsupported stateNameMap syntax; update the validator extraction before building")
        key, value = (ast.literal_eval(part) for part in match.groups())
        if key in mapping or not key or not value:
            raise ValueError("Duplicate or empty stateNameMap entry")
        mapping[key] = value
    if not mapping:
        raise ValueError("stateNameMap is empty")
    return mapping


def configured_brands(config=BRAND_CONFIG):
    brands = json.loads(Path(config).read_text(encoding="utf-8"))
    required = {"slug", "label", "column"}
    if not isinstance(brands, list) or not brands:
        raise ValueError("brand_config.json must contain a nonempty list")
    slugs, columns = set(), set()
    for brand in brands:
        if not isinstance(brand, dict) or set(brand) != required or any(
            not isinstance(brand[key], str) or not brand[key] or brand[key] != brand[key].strip()
            for key in required
        ):
            raise ValueError("Each brand requires exactly nonempty slug, label, column strings")
        slug, column = brand["slug"], brand["column"]
        if not BRAND_SLUG.fullmatch(slug):
            raise ValueError(f"Invalid brand slug: {slug!r}")
        if slug in RESERVED_BRAND_SLUGS:
            raise ValueError(f"Reserved brand slug: {slug!r}")
        if slug in slugs:
            raise ValueError(f"Duplicate brand slug: {slug!r}")
        if column in columns:
            raise ValueError(f"Duplicate brand column: {column!r}")
        slugs.add(slug)
        columns.add(column)
    return brands


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            return [], []
        return reader.fieldnames, list(reader)


def meaningful(row):
    return any(str(value or "").strip() for key, value in row.items() if key is not None)


def compare_baseline(current_rows, baseline_path):
    _, baseline_rows = read_rows(baseline_path)
    def indexed(rows):
        return {str(row.get("ID") or "").strip(): row for row in rows if meaningful(row) and row.get("ID")}
    current, baseline = indexed(current_rows), indexed(baseline_rows)
    common = current.keys() & baseline.keys()
    def signature(row):
        return {key: (value or "").strip() for key, value in row.items() if key is not None}
    return (
        sorted(current.keys() - baseline.keys()),
        sorted(baseline.keys() - current.keys()),
        sorted(key for key in common if signature(current[key]) != signature(baseline[key])),
    )


def validate(path=DEFAULT_CSV, *, config=BRAND_CONFIG, template=MAP_TEMPLATE, baseline=None):
    errors, warnings = [], []
    brands = configured_brands(config)
    mapping = state_mapping(template)
    headers, rows = read_rows(path)
    required = CORE_COLUMNS | {brand["column"] for brand in brands}
    for column in sorted(required - set(headers)):
        errors.append(f"Missing required column: {column}")
    for column in OPTIONAL_COLUMNS:
        if column not in headers:
            warnings.append(f"Missing optional column: {column}")
    if len(headers) != len(set(headers)):
        errors.append("Duplicate CSV column headers")

    seen_ids, coordinates = set(), defaultdict(list)
    store_types, states = set(), set()
    brand_counts = Counter({brand["column"]: 0 for brand in brands})
    valid, blank = 0, 0
    for line_number, row in enumerate(rows, start=2):
        if not meaningful(row):
            blank += 1
            continue
        row_errors = []
        if None in row:
            row_errors.append("extra CSV fields")
        def value(key):
            return str(row.get(key) or "").strip()
        identity = value("ID")
        if not identity:
            row_errors.append("missing ID")
        elif not ID_PATTERN.fullmatch(identity):
            row_errors.append("invalid numeric ID")
        elif identity in seen_ids:
            row_errors.append(f"duplicate ID {identity}")
        if identity:
            seen_ids.add(identity)
        for field in ("StoreName", "StoreType", "State"):
            if not value(field):
                row_errors.append(f"missing {field}")
        if value("State") and value("State") not in mapping:
            row_errors.append(f"unmapped State {value('State')!r}")
        coords = []
        for field, minimum, maximum in (("Latitude", -90, 90), ("Longitude", -180, 180)):
            try:
                number = float(value(field))
                if not math.isfinite(number) or not minimum <= number <= maximum:
                    raise ValueError
                coords.append(number)
            except ValueError:
                row_errors.append(f"invalid {field}")
        for brand in brands:
            column = brand["column"]
            flag = row.get(column) or ""
            if flag not in ("", "1"):
                row_errors.append(f"invalid {column} flag {flag!r} (expected blank or 1)")
        for field in OPTIONAL_COLUMNS:
            if field in headers and not value(field):
                warnings.append(f"Row {line_number}: missing {field}")
        if len(coords) == 2:
            lat, lng = coords
            coordinates[(lat, lng)].append(identity or f"row {line_number}")
            if not (47 <= lat <= 56 and 5 <= lng <= 16):
                warnings.append(f"Row {line_number}: coordinates outside broad Germany range")
        if row_errors:
            errors.extend(f"Row {line_number}: {error}" for error in row_errors)
            continue
        valid += 1
        store_types.add(value("StoreType"))
        states.add(mapping[value("State")])
        for brand in brands:
            if row.get(brand["column"]) == "1":
                brand_counts[brand["column"]] += 1
    for coord, ids in coordinates.items():
        if len(set(ids)) > 1:
            warnings.append(f"Identical coordinates {coord}: IDs {', '.join(ids)}")
    for brand in brands:
        if brand_counts[brand["column"]] == 0:
            errors.append(f"Configured brand {brand['slug']!r} has 0 valid locations")
    comparison = compare_baseline(rows, baseline) if baseline else None
    return {
        "brands": brands,
        "valid": valid, "blank": blank, "unique_ids": len(seen_ids),
        "store_types": len(store_types), "states": len(states),
        "brand_counts": dict(brand_counts), "errors": errors, "warnings": warnings,
        "comparison": comparison,
    }


def format_report(report):
    lines = [
        f"Valid locations: {report['valid']}",
        f"Blank rows (INFO): {report['blank']}",
        f"Unique IDs: {report['unique_ids']}",
        f"StoreTypes: {report['store_types']}",
        f"Normalized States: {report['states']}",
    ]
    lines.extend(f"Brand {name}: {count}" for name, count in report["brand_counts"].items())
    lines.append(f"Errors: {len(report['errors'])}")
    lines.extend(f"  ERROR {error}" for error in report["errors"])
    lines.append(f"Warnings: {len(report['warnings'])}")
    lines.extend(f"  WARNING {warning}" for warning in report["warnings"])
    if report["comparison"]:
        for label, values in zip(("Added IDs", "Removed IDs", "Changed IDs"), report["comparison"]):
            lines.append(f"{label}: {', '.join(values) if values else '(none)'}")
    lines.append("PASS" if not report["errors"] else "FAIL")
    return "\n".join(lines)


def validate_or_exit(path=DEFAULT_CSV, *, config=BRAND_CONFIG, template=MAP_TEMPLATE):
    try:
        report = validate(path, config=config, template=template)
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as error:
        print(f"FAIL: CSV validation could not run: {error}")
        raise SystemExit(1) from error
    print(format_report(report))
    if report["errors"]:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--baseline", type=Path, help="Compare IDs and record contents with a previous CSV")
    args = parser.parse_args()
    try:
        result = validate(args.csv, baseline=args.baseline)
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as error:
        parser.exit(1, f"FAIL: CSV validation could not run: {error}\n")
    print(format_report(result))
    raise SystemExit(bool(result["errors"]))
