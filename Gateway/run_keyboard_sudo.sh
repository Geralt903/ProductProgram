#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/home/iot/Desktop/gatewayEnv/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python not found: $PYTHON_BIN" >&2
  exit 127
fi

run_target() {
  local target="$1"
  shift || true

  if [[ ! -f "$target" ]]; then
    echo "Target file not found: $target" >&2
    exit 1
  fi

  case "$target" in
    *.py)
      exec sudo "$PYTHON_BIN" "$target" "$@"
      ;;
    *.sh)
      exec sudo bash "$target" "$@"
      ;;
    *)
      if [[ -x "$target" ]]; then
        exec sudo "$target" "$@"
      else
        echo "Unsupported file type (only .py/.sh/executable): $target" >&2
        exit 2
      fi
      ;;
  esac
}

# Direct mode:
#   ./run_keyboard_sudo.sh terminal.py
#   ./run_keyboard_sudo.sh ./terminal_latest_5s.py --arg1 ...
if [[ $# -gt 0 ]]; then
  target_arg="$1"
  shift

  if [[ "$target_arg" = /* ]]; then
    target_path="$target_arg"
  else
    target_path="$SCRIPT_DIR/$target_arg"
  fi

  run_target "$target_path" "$@"
fi

# Interactive mode: pick any runnable file in this directory.
declare -a candidates=()

while IFS= read -r -d '' f; do
  base="$(basename "$f")"
  [[ "$base" = "$(basename "$0")" ]] && continue
  candidates+=("$f")
done < <(find "$SCRIPT_DIR" -maxdepth 1 -type f \( -name "*.py" -o -name "*.sh" -o -perm -111 \) -print0 | sort -z)

if [[ ${#candidates[@]} -eq 0 ]]; then
  echo "No runnable files found in: $SCRIPT_DIR" >&2
  exit 3
fi

echo "Select a file to run:"
for i in "${!candidates[@]}"; do
  printf "  %d) %s\n" "$((i + 1))" "$(basename "${candidates[$i]}")"
done

read -rp "Enter number [1-${#candidates[@]}]: " choice
if [[ ! "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#candidates[@]} )); then
  echo "Invalid selection: $choice" >&2
  exit 4
fi

selected="${candidates[$((choice - 1))]}"
echo "Running: $(basename "$selected")"
run_target "$selected"
