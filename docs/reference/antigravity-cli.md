# Antigravity CLI integration reference

Captured 2026-07-18. Verify current behavior against the upstream documentation and `agy --help`
before changing Forge's adapter.

## Supported contract

- Binary: `agy`
- Install: <https://antigravity.google/docs/cli-install>
- Source: <https://github.com/google-antigravity/antigravity-cli>
- Authentication: launch `agy`; use browser Google Sign-In locally or the printed URL/code flow on
  SSH. Credentials remain in the provider-owned system-keyring integration.
- Readiness without inference: `agy models` returns a non-empty catalog when authenticated and a
  sign-in instruction with non-zero exit when no session exists.
- Headless prompt: place `--print <prompt>` after every other flag.
- Safe write mode: `--mode accept-edits --sandbox`.
- Read-only mode: `--mode plan --sandbox`.
- Unsafe mode: `--mode accept-edits --dangerously-skip-permissions`; external isolation and Forge's
  explicit unsafe consent are required.

Antigravity's sandbox constrains terminal execution. File access is separately governed by its
permission engine and non-workspace-access setting. In print mode, unapproved commands can be
denied because there is no interactive approval surface.
