#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYOUT="${D2_LAYOUT:-elk}"

if ! command -v d2 >/dev/null 2>&1; then
  echo "d2 is not installed or not on PATH" >&2
  exit 127
fi

FONT_ARGS=()
for font in   "$DIR/fonts/InterVariable.ttf"   "$DIR/fonts/InterVar.ttf"   "$DIR/fonts/Inter.ttf"   "$DIR/fonts/Inter-VariableFont_opsz,wght.ttf"; do
  if [[ -f "$font" ]]; then
    FONT_ARGS=(--font-regular "$font" --font-bold "$font" --font-italic "$font")
    break
  fi
done

if [[ "$#" -gt 0 ]]; then
  files=("$@")
else
  files=("$DIR"/*.d2)
fi

for input in "${files[@]}"; do
  [[ -e "$input" ]] || continue
  [[ "$(basename "$input")" == "styles.d2" ]] && continue
  output="${input%.d2}.svg"
  cmd=(d2 --layout "$LAYOUT")
  if [[ ${#FONT_ARGS[@]} -gt 0 ]]; then
    cmd+=("${FONT_ARGS[@]}")
  fi
  cmd+=("$input" "$output")
  "${cmd[@]}"
done
