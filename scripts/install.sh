#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
STAMP_FILE="$VENV_DIR/.forge-install-stamp"
DEPENDENCIES=(
  "typer>=0.15.0"
  "rich>=13.0.0"
  "questionary>=2.1.0"
)

create_venv() {
  if [ -x "$VENV_DIR/bin/python" ]; then
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 --seed "$VENV_DIR"
    return
  fi

  local python_cmd=""
  if command -v python3.12 >/dev/null 2>&1; then
    python_cmd="python3.12"
  elif command -v python3 >/dev/null 2>&1; then
    python_cmd="python3"
  else
    echo "Python 3.12+ is required. Install uv or python3.12 and try again." >&2
    exit 1
  fi

  if ! "$python_cmd" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
  then
    echo "Python 3.12+ is required. Install uv or python3.12 and try again." >&2
    exit 1
  fi

  "$python_cmd" -m venv "$VENV_DIR"
}

install_forge() {
  if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
    "$VENV_DIR/bin/python" -m ensurepip --upgrade
  fi

  if ! "$VENV_DIR/bin/python" - <<'PY'
from importlib.metadata import PackageNotFoundError, version

requirements = {
    "typer": (0, 15, 0),
    "rich": (13, 0, 0),
    "questionary": (2, 1, 0),
}


def parse_version(raw: str) -> tuple[int, int, int]:
    parts: list[int] = []
    for part in raw.split("."):
        digits = []
        for char in part:
            if char.isdigit():
                digits.append(char)
            else:
                break
        parts.append(int("".join(digits) or "0"))
        if len(parts) == 3:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


for package, minimum in requirements.items():
    try:
        installed = parse_version(version(package))
    except PackageNotFoundError:
        raise SystemExit(1)
    if installed < minimum:
        raise SystemExit(1)
PY
  then
    "$VENV_DIR/bin/python" -m pip install --upgrade "${DEPENDENCIES[@]}"
  fi

  cat > "$VENV_DIR/bin/forge" <<EOF
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$ROOT_DIR"
VENV_DIR="$VENV_DIR"

export PYTHONPATH="\$ROOT_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
exec "\$VENV_DIR/bin/python" -m ubundiforge "\$@"
EOF

  chmod +x "$VENV_DIR/bin/forge"
  touch "$STAMP_FILE"
}

create_venv
install_forge

cat <<EOF
Forge is installed in $VENV_DIR

Run it with:
  $VENV_DIR/bin/forge --version
  $VENV_DIR/bin/forge

Or activate the environment:
  source "$VENV_DIR/bin/activate"
  forge --version
EOF
