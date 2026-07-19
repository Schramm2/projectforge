# Antigravity CLI integration reference

Captured 2026-07-19 against Antigravity CLI 1.1.4. Verify current behavior against the upstream
documentation and `agy --help` before changing Forge's adapter.

## Supported contract

- Binary: `agy`
- Install: <https://antigravity.google/docs/cli-install>
- Source: <https://github.com/google-antigravity/antigravity-cli>
- Authentication: launch `agy`; use browser Google Sign-In locally or the printed URL/code flow on
  SSH. Credentials remain in the provider-owned system-keyring integration.
- Readiness without inference: `agy models` returns a non-empty catalog when authenticated and a
  sign-in instruction with non-zero exit when no session exists.
- Workspace binding: pass `--add-dir <absolute-workspace>`; `agy` can otherwise attach print-mode work to its own scratch project even when Forge sets the subprocess cwd.
- Headless prompt: place `--print <prompt>` after every other flag.
- Safe write mode: `--mode accept-edits --sandbox` plus a provider permission rule allowing `write_file(<workspace>)`.
- Read-only mode: `--mode plan --sandbox`.
- Unsafe mode: `--mode accept-edits --dangerously-skip-permissions`; external isolation and Forge's
  explicit unsafe consent are required.

Antigravity's sandbox constrains terminal execution. File access is separately governed by its
permission engine. Official permissions documentation says unconfigured actions default to Ask;
print mode cannot answer that prompt, so a safe headless run can otherwise deny `write_file` and
still exit 0 with no workspace change.

Forge manages this automatically. For the duration of a safe-mode run it adds a narrow
`write_file(<workspace>)` allow-rule (never `write_file(*)`) to `~/.gemini/antigravity-cli/settings.json`,
merging non-destructively with any existing user settings, then restores the file to its exact prior
state (removing it if Forge created it) once the run finishes. The grant is reference-counted so
concurrent phases sharing one workspace add the rule once. See
`src/projectforge/provider_permissions.py`. The exit-0-with-denial detection remains as a safety net
for plan mode or a settings file Forge cannot write; Forge treats that provider response as a
permission failure.
