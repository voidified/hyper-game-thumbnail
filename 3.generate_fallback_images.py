#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


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


def iter_image_files(src_dir: Path) -> list[Path]:
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif"}
    files: list[Path] = []
    for p in sorted(src_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in allowed_exts:
            files.append(p)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resize assets/Fallbacks images to generated/s3 while preserving filenames"
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base directory for source/output relative paths (default: current dir)",
    )
    parser.add_argument(
        "--src-dir",
        default="assets/Fallbacks",
        help="Source directory containing fallback images (default: assets/Fallbacks)",
    )
    parser.add_argument(
        "--out-dir",
        default="generated/s3",
        help="Output directory (default: generated/s3)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N images (0 means all)",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()

    src_dir = Path(args.src_dir)
    if not src_dir.is_absolute():
        src_dir = (base_dir / src_dir).resolve()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (base_dir / out_dir).resolve()

    if not src_dir.exists() or not src_dir.is_dir():
        print(f"source directory not found: {src_dir}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    files = iter_image_files(src_dir)
    total = len(files)
    processed = 0
    converted = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    for src in files:
        if args.limit > 0 and processed >= args.limit:
            break

        dst = out_dir / f"{src.stem}.jpg"
        processed += 1

        ok, err = run_magick(src, dst)
        if ok:
            converted += 1
        else:
            failed += 1
            failures.append((src.name, err[:300]))

    print(f"src_dir={src_dir}")
    print(f"out_dir={out_dir}")
    print(f"total_images={total}")
    print(f"processed={processed}")
    print(f"converted={converted}")
    print(f"failed={failed}")

    if failures:
        print("failure_samples:")
        for name, reason in failures[:20]:
            print(f"file={name} reason={reason}")


if __name__ == "__main__":
    main()
