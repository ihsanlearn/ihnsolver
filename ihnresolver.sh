#!/usr/bin/env bash
# Resolve + Live host checker (tanpa alterx)
# Usage:
#   ./resolve-live.sh [-i subdomains.txt] [-o live-hosts.txt] [-S sample] [-p pattern]
# Output tambahan: httpx-alive.txt (berisi hasil mentah httpx)
set -euo pipefail
IFS=$'\n\t'

# Defaults
INPUT_FILE="subdomains.txt"
OUTPUT_FILE="live-hosts.txt"
SAMPLE_LIMIT=0
PRIORITY_PATTERN=""
CONCURRENCY="${CONCURRENCY:-30}"
DNSX_THREADS="${DNSX_THREADS:-50}"
HTTPX_THREADS="${HTTPX_THREADS:-$CONCURRENCY}"
TIMEOUT="${TIMEOUT:-5}"

usage() {
  cat <<EOF
Usage: $0 [-i input] [-o output] [-S sample] [-p pattern]
  -i FILE    Input file (default: $INPUT_FILE)
  -o FILE    Output file (default: $OUTPUT_FILE)
  -S N       Sample top N results (0=disabled)
  -p PAT     Regex untuk filter hasil (mis. 'api|admin|login')
EOF
  exit 1
}

while getopts ":i:o:S:p:h" opt; do
  case $opt in
    i) INPUT_FILE="$OPTARG" ;;
    o) OUTPUT_FILE="$OPTARG" ;;
    S) SAMPLE_LIMIT="$OPTARG" ;;
    p) PRIORITY_PATTERN="$OPTARG" ;;
    h|*) usage ;;
  esac
done

if [ ! -s "$INPUT_FILE" ]; then
  echo "[!] File tidak ditemukan atau kosong: $INPUT_FILE" >&2
  exit 1
fi

TMPDIR="$(mktemp -d -t livecheck.XXXXXX)"
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

command_exists() { command -v "$1" >/dev/null 2>&1; }

echo "[*] Tool availability:"
for t in dnsx httpx curl dig xargs; do
  printf "    %-8s: %s\n" "$t" "$(command_exists "$t" && echo yes || echo no)"
done
echo

DEDUP="$TMPDIR/dedup.txt"
awk '{gsub(/^[[:space:]]+|[[:space:]]+$/,""); if(length) print tolower($0)}' "$INPUT_FILE" \
  | sort -u > "$DEDUP"
echo "[*] Deduped input: $(wc -l < "$DEDUP") lines"

ENRICHED="$TMPDIR/enriched.txt"
cp "$DEDUP" "$ENRICHED"

if [ -n "$PRIORITY_PATTERN" ]; then
  echo "[*] Filtering pattern: $PRIORITY_PATTERN"
  grep -E -i "$PRIORITY_PATTERN" "$ENRICHED" | sort -u > "$TMPDIR/prioritized.txt"
  if [ -s "$TMPDIR/prioritized.txt" ]; then
    mv "$TMPDIR/prioritized.txt" "$ENRICHED"
  fi
fi

if [ "$SAMPLE_LIMIT" -gt 0 ]; then
  echo "[*] Sampling top $SAMPLE_LIMIT entries..."
  head -n "$SAMPLE_LIMIT" "$ENRICHED" > "$TMPDIR/sample.txt"
  mv "$TMPDIR/sample.txt" "$ENRICHED"
fi

RESOLVED="$TMPDIR/resolved.txt"
if command_exists dnsx; then
  echo "[*] Resolving with dnsx ..."
  cat "$ENRICHED" | dnsx -silent -a -aaaa -resp -threads "$DNSX_THREADS" 2>/dev/null \
    | awk '{print $1}' | sed '/^\s*$/d' | sort -u > "$RESOLVED"
else
  echo "[*] dnsx not found — fallback dig"
  > "$RESOLVED"
  while IFS= read -r host; do
    if dig +short A "$host" | grep -q '.' || dig +short AAAA "$host" | grep -q '.'; then
      echo "$host"
    fi
  done < "$ENRICHED" | sort -u > "$RESOLVED"
fi
echo "[*] Resolved count: $(wc -l < "$RESOLVED")"

ALIVE_RAW="httpx-alive.txt"
ALIVE="$TMPDIR/httpx-alive-clean.txt"
> "$ALIVE_RAW"

if command_exists httpx; then
  echo "[*] Running httpx (timeout=${TIMEOUT}s threads=${HTTPX_THREADS}) ..."
  cat "$RESOLVED" \
    | httpx -silent -status-code -title -tech-detect -timeout "$TIMEOUT" -threads "$HTTPX_THREADS" 2>/dev/null \
    | tee -a "$ALIVE_RAW" \
    | awk '{print $1}' | sed '/^\s*$/d' | sort -u > "$ALIVE"
else
  echo "[*] httpx not found — fallback to curl"
  cat "$RESOLVED" \
    | xargs -n1 -P "$CONCURRENCY" -I{} bash -c '
      h="{}"
      if curl -Is --max-time '"$TIMEOUT"' "https://$h" 2>/dev/null | head -n1 | grep -q "^HTTP/"; then
        echo "https://$h"
      elif curl -Is --max-time '"$TIMEOUT"' "http://$h" 2>/dev/null | head -n1 | grep -q "^HTTP/"; then
        echo "http://$h"
      fi
    ' | sort -u > "$ALIVE"
fi

sed 's:/*$::' "$ALIVE" | sort -u > "$OUTPUT_FILE"

echo
echo "[*] Done."
echo "[*] Resolved: $(wc -l < "$RESOLVED")"
echo "[*] Live hosts: $(wc -l < "$OUTPUT_FILE")"
echo "[*] Output file: $OUTPUT_FILE"
echo "[*] Full httpx details: $ALIVE_RAW"