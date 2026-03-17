#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV is empty: {path}")

    header = [col.strip() for col in rows[0]]
    data: list[dict[str, str]] = []

    for row in rows[1:]:
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        record = {header[idx]: row[idx].strip() for idx in range(len(header))}
        data.append(record)

    return header, data


def row_key(row: dict[str, str]) -> tuple[str, str]:
    provider = row.get("provider", "").strip().lower()
    game_id = row.get("game_id", "").strip().lower()
    return provider, game_id


def ensure_required_columns(header: list[str], source_name: str) -> None:
    normalized = {h.strip().lower() for h in header}
    missing = [c for c in ("provider", "game_id") if c not in normalized]
    if missing:
        cols = ", ".join(missing)
        raise ValueError(f"Missing required columns in {source_name}: {cols}")


def merge_csv(base_path: Path, append_path: Path, output_path: Path) -> int:
    base_header, base_rows = read_csv(base_path)
    append_header, append_rows = read_csv(append_path)

    ensure_required_columns(base_header, str(base_path))
    ensure_required_columns(append_header, str(append_path))

    out_header = list(base_header)
    for col in append_header:
        if col not in out_header:
            out_header.append(col)

    merged: dict[tuple[str, str], dict[str, str]] = {}
    for row in base_rows:
        merged[row_key(row)] = row
    for row in append_rows:
        merged[row_key(row)] = row

    sorted_rows = sorted(
        merged.values(),
        key=lambda row: (
            row.get("provider", "").strip().lower(),
            row.get("game_id", "").strip().lower(),
        ),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(out_header)
        for row in sorted_rows:
            writer.writerow([row.get(col, "") for col in out_header])

    return len(sorted_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Merge base and append CSV by (provider,game_id). "
            "Rows from append override base on duplicate keys."
        )
    )
    parser.add_argument(
        "--base",
        default="games.csv",
        help="Base CSV path (default: games.csv)",
    )
    parser.add_argument(
        "--append",
        default="games_append.csv",
        help="Append CSV path (default: games_append.csv)",
    )
    parser.add_argument(
        "--output",
        default="games_output.csv",
        help="Output CSV path (default: games_output.csv)",
    )
    args = parser.parse_args()

    base_path = Path(args.base)
    append_path = Path(args.append)
    output_path = Path(args.output)

    count = merge_csv(base_path, append_path, output_path)
    print(f"Wrote merged CSV: {output_path}")
    print(f"Rows written: {count}")


if __name__ == "__main__":
    main()
