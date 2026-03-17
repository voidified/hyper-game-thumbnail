#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="${1:-pp_slot_images.txt}"
OUTPUT_ROOT="${2:-assets/Others/Pragmatic}"
INTERVAL_SECONDS=0.3
REQUEST_COUNT=0

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "[ERROR] Input file not found: $INPUT_FILE" >&2
  exit 1
fi

while IFS= read -r url || [[ -n "$url" ]]; do
  url="${url%$'\r'}"
  [[ -z "$url" ]] && continue
  [[ "$url" =~ ^[[:space:]]*# ]] && continue

  prefix="https://common-static.ppgames.net/gs2c/common/lobby/v1/apps/slots-lobby-assets/"
  if [[ "$url" != "$prefix"* ]]; then
    echo "[WARN] Unexpected URL format, skipping: $url" >&2
    continue
  fi

  relative_path="${url#$prefix}"
  game_id="${relative_path%%/*}"
  file_name="${relative_path##*/}"

  if [[ -z "$game_id" || -z "$file_name" || "$relative_path" == "$url" ]]; then
    echo "[WARN] Could not parse URL path, skipping: $url" >&2
    continue
  fi

  out_dir="$OUTPUT_ROOT/$game_id"
  out_file="$out_dir/$file_name"

  if [[ -f "$out_file" ]]; then
    echo "[SKIP] Exists: $out_file"
    continue
  fi

  mkdir -p "$out_dir"

  if [[ "$REQUEST_COUNT" -gt 0 ]]; then
    sleep "$INTERVAL_SECONDS"
  fi

  if curl -fL --retry 3 --connect-timeout 20 -o "$out_file" "$url"; then
    echo "[OK] $url -> $out_file"
  else
    echo "[FAIL] $url" >&2
  fi
  REQUEST_COUNT=$((REQUEST_COUNT + 1))
done < "$INPUT_FILE"
