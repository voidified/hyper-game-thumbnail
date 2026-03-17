#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

FIXED_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)
FIXED_REFERER = "https://share.dc-ace.com/"

# python3 a.download_dcace_images.py \
#   --urls-file "tmp.dcace.urls.txt" \
#   --cookie 'cf_clearance=...' \
#   --interval-seconds 1.0

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download image URLs with curl and store under assets/<vendor>/... "
            "while preserving URL path structure"
        )
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="Image URLs to download",
    )
    parser.add_argument(
        "--urls-file",
        action="append",
        default=[],
        help="Path to a text file with one URL per line (blank lines and # comments ignored)",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help='Custom curl header, e.g. --header "Authorization: Bearer <token>"',
    )
    parser.add_argument(
        "--auth-header-name",
        default="",
        help="Authentication header name (optional)",
    )
    parser.add_argument(
        "--auth-header-value",
        default="",
        help="Authentication header value (optional)",
    )
    parser.add_argument(
        "--assets-root",
        default="assets",
        help="Base folder to save files (default: assets)",
    )
    parser.add_argument(
        "--cookie",
        default="",
        help="Cookie value only, e.g. 'cf_clearance=...'; converted to Cookie header",
    )
    parser.add_argument(
        "--headers-file",
        default="",
        help=(
            "Path to raw header file. Supports both 'Key: Value' lines and "
            "pasted browser style alternating key/value lines."
        ),
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Delay between downloads in seconds (default: 1.0)",
    )
    return parser.parse_args()


def host_to_vendor(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[0].lower() == "storage":
        core = parts[1]
    elif len(parts) >= 2:
        core = parts[-2]
    else:
        core = host

    cleaned = "".join(ch for ch in core if ch.isalnum())
    if not cleaned:
        return "Unknown"
    return cleaned[:1].upper() + cleaned[1:]


def sanitize_unix_segment(raw_segment: str, url: str) -> str:
    removed: list[str] = []
    cleaned_chars: list[str] = []

    for ch in raw_segment:
        if ch == "/" or ord(ch) == 0 or ord(ch) < 32:
            removed.append(ch)
            continue
        cleaned_chars.append(ch)

    if removed:
        printable = ", ".join(repr(ch) for ch in removed)
        print(
            "[WARN] Removed unix-invalid chars "
            f"({printable}) from path segment '{raw_segment}' in URL: {url}",
            file=sys.stderr,
        )

    sanitized = "".join(cleaned_chars).strip()
    return sanitized or "_"


def url_to_local_path(url: str, assets_root: Path) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    vendor = host_to_vendor(parsed.netloc)
    decoded_segments = [
        unquote(seg) for seg in parsed.path.split("/") if seg.strip() != ""
    ]

    if decoded_segments and decoded_segments[0].lower() == "prod":
        decoded_segments = decoded_segments[1:]

    if not decoded_segments:
        raise ValueError(f"URL path has no file name: {url}")

    sanitized_segments = [sanitize_unix_segment(seg, url) for seg in decoded_segments]
    return assets_root / vendor / Path(*sanitized_segments)


def build_headers(args: argparse.Namespace) -> list[str]:
    headers = [
        f"User-Agent: {FIXED_USER_AGENT}",
        f"Referer: {FIXED_REFERER}",
    ]
    headers.extend(filter_disallowed_headers(args.header))

    if args.headers_file:
        headers.extend(filter_disallowed_headers(load_headers_file(Path(args.headers_file))))

    if args.cookie:
        headers.append(f"Cookie: {args.cookie}")

    if args.auth_header_name and args.auth_header_value:
        headers.append(f"{args.auth_header_name}: {args.auth_header_value}")
    elif args.auth_header_name or args.auth_header_value:
        raise ValueError(
            "Both --auth-header-name and --auth-header-value are required together"
        )
    return headers


def filter_disallowed_headers(headers: list[str]) -> list[str]:
    allowed: list[str] = []
    for header in headers:
        key = header.split(":", 1)[0].strip().lower()
        if key in {"user-agent", "referer"}:
            print(
                f"[WARN] Ignoring custom header '{key}' because it is fixed in script.",
                file=sys.stderr,
            )
            continue
        allowed.append(header)
    return allowed


def load_headers_file(file_path: Path) -> list[str]:
    if not file_path.is_file():
        raise ValueError(f"Headers file not found: {file_path}")

    raw_lines = file_path.read_text(encoding="utf-8").splitlines()
    lines = [line.strip() for line in raw_lines if line.strip()]
    headers: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if ":" in line and not line.startswith(":"):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            i += 1
        else:
            if i + 1 >= len(lines):
                print(
                    f"[WARN] Ignoring dangling header key without value: {line}",
                    file=sys.stderr,
                )
                break
            key = lines[i]
            value = lines[i + 1]
            i += 2

        if key.startswith(":"):
            continue

        key_lower = key.lower()
        if key_lower in {
            "authority",
            "method",
            "path",
            "scheme",
            "if-none-match",
            "if-modified-since",
        }:
            continue

        headers.append(f"{key}: {value}")

    return headers


def load_urls_file(file_path: Path) -> list[str]:
    if not file_path.is_file():
        raise ValueError(f"URLs file not found: {file_path}")

    urls: list[str] = []
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def collect_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.urls)
    for file_str in args.urls_file:
        urls.extend(load_urls_file(Path(file_str)))
    return urls


def download_with_curl(url: str, out_path: Path, headers: list[str]) -> tuple[bool, str]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["curl", "-fL", "--retry", "3", "--connect-timeout", "20", "-o", str(out_path)]
    for header in headers:
        cmd.extend(["-H", header])
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Unknown curl error"
        return False, detail
    return True, ""


def main() -> int:
    args = parse_args()
    assets_root = Path(args.assets_root)

    try:
        headers = build_headers(args)
        urls = collect_urls(args)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    if not urls:
        print(
            "[ERROR] No URLs provided. Use positional URLs and/or --urls-file.",
            file=sys.stderr,
        )
        return 2

    failed = False
    request_count = 0
    for url in urls:
        try:
            out_path = url_to_local_path(url, assets_root)
        except ValueError as exc:
            failed = True
            print(f"[ERROR] {exc}", file=sys.stderr)
            continue

        if out_path.is_file():
            print(f"[SKIP] Exists: {out_path}")
            continue

        if request_count > 0 and args.interval_seconds > 0:
            time.sleep(args.interval_seconds)

        ok, err = download_with_curl(url, out_path, headers)
        request_count += 1
        if ok:
            print(f"[OK] {url} -> {out_path}")
        else:
            failed = True
            print(f"[FAIL] {url}", file=sys.stderr)
            print(f"       {err}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
