#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${FORGE_BACKEND:-}" ]]; then
  echo "Set FORGE_BACKEND to an authenticated backend: claude, gemini, or codex." >&2
  exit 2
fi

demo_root="${1:-/tmp/projectforge-terminal-demo}"
project_name="hello-forge"
project_dir="${demo_root}/${project_name}"

if [[ -e "${demo_root}" ]]; then
  echo "Refusing to overwrite existing demo directory: ${demo_root}" >&2
  exit 2
fi

mkdir -p "${demo_root}"

uv tool install --force git+https://github.com/Schramm2/projectforge.git@v0.4.1
forge --version

forge --dry-run \
  --use "${FORGE_BACKEND}" \
  --name "${project_name}" \
  --stack python-cli \
  --description "A tiny greeting CLI" \
  --no-docker \
  --no-open \
  --no-verify

cd "${demo_root}"
forge \
  --use "${FORGE_BACKEND}" \
  --name "${project_name}" \
  --stack python-cli \
  --description "A tiny greeting CLI" \
  --no-docker \
  --no-open \
  --verify

test -f "${project_dir}/.forge/scaffold.json"
test -f "${project_dir}/README.md"
git -C "${project_dir}" status --short --branch

echo "Verified scaffold: ${project_dir}"
