#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${FORGE_BACKEND:-}" ]]; then
  echo "Set FORGE_BACKEND to an authenticated backend: claude, gemini, or codex." >&2
  exit 2
fi

demo_root="${1:-/tmp/projectforge-terminal-demo}"
project_name="hello-forge"
project_dir="${demo_root}/${project_name}"
tool_dir="${demo_root}/.uv-tools"
tool_bin_dir="${demo_root}/.uv-bin"
tool_cache_dir="${demo_root}/.uv-cache"
forge_bin="${tool_bin_dir}/forge"
backend_args=(--use "${FORGE_BACKEND}")

if [[ -n "${FORGE_MODEL:-}" ]]; then
  backend_args+=(--model "${FORGE_MODEL}")
fi

if [[ -e "${demo_root}" ]]; then
  echo "Refusing to overwrite existing demo directory: ${demo_root}" >&2
  exit 2
fi

mkdir -p "${demo_root}"

UV_TOOL_DIR="${tool_dir}" \
UV_TOOL_BIN_DIR="${tool_bin_dir}" \
UV_CACHE_DIR="${tool_cache_dir}" \
uv tool install --python 3.12 --no-config \
  https://github.com/Schramm2/projectforge/archive/refs/tags/v0.4.1.tar.gz
"${forge_bin}" --version

"${forge_bin}" --dry-run \
  "${backend_args[@]}" \
  --name "${project_name}" \
  --stack python-cli \
  --description "A tiny greeting CLI" \
  --no-docker \
  --no-open \
  --no-verify

cd "${demo_root}"
"${forge_bin}" \
  "${backend_args[@]}" \
  --name "${project_name}" \
  --stack python-cli \
  --description "A tiny greeting CLI" \
  --no-docker \
  --no-ci \
  --no-open \
  --verify \
  --no-agents \
  --extra "Keep the scaffold minimal. Implement a greet command, tests, Ruff and mypy configuration, and no network-dependent runtime behavior."

test -f "${project_dir}/.forge/scaffold.json"
test -f "${project_dir}/README.md"
(
  cd "${project_dir}"
  uv sync --extra dev
  uv run ruff check .
  uv run pytest -q
  uv run mypy src tests
  uv run hello-forge greet Ada
)
git -C "${project_dir}" status --short --branch

echo "Verified scaffold: ${project_dir}"
