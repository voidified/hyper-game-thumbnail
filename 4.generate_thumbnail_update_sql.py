#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def build_game_id_map(platform_csv_path: Path) -> dict[tuple[str, str], str]:
    game_id_map: dict[tuple[str, str], str] = {}

    with platform_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db_id = (row.get("id") or "").strip()
            provider = (row.get("provider") or "").strip()
            game_id = (row.get("game_id") or "").strip()

            if not db_id or not provider or not game_id:
                continue

            game_id_map[(provider, game_id)] = db_id

    return game_id_map


def build_rows(
    platform_csv_path: Path,
    hashed_csv_path: Path,
    s3_dir: Path,
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen_ids: set[str] = set()
    game_id_map = build_game_id_map(platform_csv_path)

    with hashed_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            provider = (row.get("provider") or "").strip()
            game_id = (row.get("game_id") or "").strip()
            hashed = (row.get("hashed") or "").strip()

            if not provider or not game_id or not hashed:
                continue

            db_id = game_id_map.get((provider, game_id))
            if not db_id:
                continue

            if db_id in seen_ids:
                continue

            if not (s3_dir / f"{hashed}.jpg").is_file():
                continue

            seen_ids.add(db_id)
            rows.append((db_id, hashed))

    return rows


def build_sql(rows: list[tuple[str, str]], cdn_base: str) -> str:
    lines: list[str] = []
    lines.append('UPDATE platform.games')
    lines.append('SET "thumbnail_url_hyper" = NULL;')
    lines.append("")

    if not rows:
        lines.append("-- No valid rows found in input CSV.")
        return "\n".join(lines) + "\n"

    lines.append('UPDATE platform.games')
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
        description=(
            "Generate SQL to update games.thumbnail_url_hyper by joining "
            "platform export and hashed CSV"
        )
    )
    parser.add_argument(
        "--platform-csv",
        default="platform_games_export_2026-02-27_162847.csv",
        help="Platform export CSV path",
    )
    parser.add_argument(
        "--hashed-csv",
        default="generated/hashed.csv",
        help="Hashed CSV path",
    )
    parser.add_argument(
        "--s3-dir",
        default="generated/s3",
        help="Directory containing <hash>.jpg files",
    )
    parser.add_argument(
        "--output",
        default="generated/update_games_thumbnail_url.sql",
        help="Output SQL path (default: update_games_thumbnail_url.sql)",
    )
    parser.add_argument(
        "--cdn-base",
        default="https://d13ko3zh1icget.cloudfront.net/game_thumbnail_images",
        help="Base URL prefix for thumbnail_url",
    )
    args = parser.parse_args()

    platform_csv_path = Path(args.platform_csv)
    hashed_csv_path = Path(args.hashed_csv)
    s3_dir = Path(args.s3_dir)
    out_path = Path(args.output)
    rows = build_rows(platform_csv_path, hashed_csv_path, s3_dir)
    sql = build_sql(rows, args.cdn_base.rstrip("/"))
    out_path.write_text(sql, encoding="utf-8")

    print(f"Wrote SQL: {out_path}")
    print(f"Rows included: {len(rows)}")


if __name__ == "__main__":
    main()
