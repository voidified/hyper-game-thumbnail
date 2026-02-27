#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def build_rows(csv_path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen_ids: set[str] = set()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            game_id = (row.get("id") or "").strip()
            hashed = (row.get("hashed") or "").strip()

            if not game_id or not hashed:
                continue

            if game_id in seen_ids:
                continue

            seen_ids.add(game_id)
            rows.append((game_id, hashed))

    return rows


def build_sql(rows: list[tuple[str, str]], cdn_base: str) -> str:
    lines: list[str] = []
    lines.append('UPDATE "platform.games"')
    lines.append('SET "thumbnail_url_hyper" = NULL;')
    lines.append("")

    if not rows:
        lines.append("-- No valid rows found in input CSV.")
        return "\n".join(lines) + "\n"

    lines.append('UPDATE "platform.games"')
    lines.append('SET "thumbnail_url_hyper" = CASE "id"')
    for game_id, hashed in rows:
        url = f"{cdn_base}/{hashed}.jpg"
        lines.append(f"    WHEN '{game_id}' THEN '{url}'")
    lines.append("END")
    lines.append('WHERE "id" IN (')
    for idx, (game_id, _) in enumerate(rows):
        suffix = "," if idx < len(rows) - 1 else ""
        lines.append(f"    '{game_id}'{suffix}")
    lines.append(");")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate SQL to update games.thumbnail_url_hyper from hashed.csv"
    )
    parser.add_argument(
        "--input",
        default="generated/hashed.csv",
        help="Input CSV path (default: hashed.csv)",
    )
    parser.add_argument(
        "--output",
        default="update_games_thumbnail_url.sql",
        help="Output SQL path (default: update_games_thumbnail_url.sql)",
    )
    parser.add_argument(
        "--cdn-base",
        default="https://d13ko3zh1icget.cloudfront.net/game_thumbnail_images",
        help="Base URL prefix for thumbnail_url",
    )
    args = parser.parse_args()

    csv_path = Path(args.input)
    out_path = Path(args.output)
    rows = build_rows(csv_path)
    sql = build_sql(rows, args.cdn_base.rstrip("/"))
    out_path.write_text(sql, encoding="utf-8")

    print(f"Wrote SQL: {out_path}")
    print(f"Rows included: {len(rows)}")


if __name__ == "__main__":
    main()
