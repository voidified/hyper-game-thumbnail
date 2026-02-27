#!/usr/bin/env python3
import argparse
import csv
import hashlib
import subprocess
from pathlib import Path


def md5_key(provider: str, game_id: str) -> str:
    raw = f"{provider.strip().lower()}|{game_id.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def run_magick(src: Path, dst: Path) -> tuple[bool, str]:
    cmd = [
        "magick",
        str(src),
        "-resize",
        "300x>",
        "-quality",
        "80",
        "-strip",
        "-interlace",
        "Plane",
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, ""
    return False, (proc.stderr or proc.stdout).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert matched_file images to generated/s3/{md5(provider|game_id)}.jpg"
    )
    parser.add_argument(
        "--csv",
        default="generated/hashed.csv",
        help="Input CSV path (default: hashed.csv)",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base directory for matched_file relative paths (default: current dir)",
    )
    parser.add_argument(
        "--out-dir",
        default="generated/s3",
        help="Output directory prefix for hashed files (default: generated/s3)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N rows with matched_file (0 means all)",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = (base_dir / csv_path).resolve()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (base_dir / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    with_matched = 0
    converted = 0
    missing_source = 0
    failed = 0
    processed = 0

    failures: list[tuple[int, str, str]] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            total_rows += 1

            matched_file = (row.get("downloaded_file") or "").strip()
            if not matched_file:
                continue

            with_matched += 1
            if args.limit > 0 and processed >= args.limit:
                continue

            provider = row.get("provider") or ""
            game_id = row.get("game_id") or ""
            digest = md5_key(provider, game_id)

            src = (base_dir / matched_file).resolve()
            dst = out_dir / f"{digest}.jpg"

            processed += 1
            if not src.exists():
                missing_source += 1
                failures.append((line_no, matched_file, "missing source"))
                continue

            ok, err = run_magick(src, dst)
            if ok:
                converted += 1
            else:
                failed += 1
                failures.append((line_no, matched_file, err[:300]))

    print(f"csv={csv_path}")
    print(f"out_dir={out_dir}")
    print(f"total_rows={total_rows}")
    print(f"rows_with_matched_file={with_matched}")
    print(f"processed={processed}")
    print(f"converted={converted}")
    print(f"missing_source={missing_source}")
    print(f"failed={failed}")

    if failures:
        print("failure_samples:")
        for line_no, matched_file, reason in failures[:20]:
            print(f"line={line_no} matched_file={matched_file} reason={reason}")


if __name__ == "__main__":
    main()
