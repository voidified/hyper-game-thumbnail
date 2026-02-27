#!/usr/bin/env python3
import argparse
import csv
import hashlib
from pathlib import Path


def build_hashed_csv(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Input CSV is empty")

    header = rows[0]
    normalized = [h.strip().lower() for h in header]

    try:
        provider_idx = normalized.index("provider")
        game_id_idx = normalized.index("game_id")
        matched_file_idx = normalized.index("downloaded_file")
    except ValueError as exc:
        raise ValueError(f"Required column not found: {exc}") from exc

    out_rows = [header + ["hashed"]]

    for row in rows[1:]:
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))

        matched_file = row[matched_file_idx].strip() if matched_file_idx < len(row) else ""

        if matched_file == "":
            hashed = ""
        else:
            provider = row[provider_idx].strip().lower() if provider_idx < len(row) else ""
            game_id = row[game_id_idx].strip().lower() if game_id_idx < len(row) else ""
            raw = f"{provider}|{game_id}"
            hashed = hashlib.md5(raw.encode("utf-8")).hexdigest()

        out_rows.append(row + [hashed])

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(out_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add hashed column using md5(lower(provider)|lower(game_id))."
    )
    parser.add_argument(
        "--input",
        default="games.csv",
        help="Input CSV path (default: game_thumbnail_mapping.csv)",
    )
    parser.add_argument(
        "--output",
        default="generated/hashed.csv",
        help="Output CSV path (default: hashed.csv)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    build_hashed_csv(input_path, output_path)
    print(f"Wrote hashed CSV: {output_path}")


if __name__ == "__main__":
    main()
