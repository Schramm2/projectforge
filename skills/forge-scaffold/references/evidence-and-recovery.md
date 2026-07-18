# Evidence, Privacy, and Recovery

## Durable scaffold evidence

Inspect structured fields, not entire files by default:

- `.forge/scaffold.json` — Forge version, requested project facts, routing, model override behavior,
  approval mode, convention bundle hash, and ordered convention source metadata.
- `.forge/conventions-snapshot.md` — exact effective instructions for replay. Treat as potentially
  private; do not paste it into external messages by default.
- `.forge/verification.json` — commands, portable working directories, timeouts, skip reasons,
  exits, health attempts, concise details, and remediation.
- `.forge/replay-diff-<date>.md` — comparison output only when replay diff was requested.

Prefer a field-selecting JSON tool or a small local parser. Do not dump environment files, provider
configuration, auth status payloads, or unredacted logs.

## Independent verification

Use commands recorded by `.forge/verification.json`, the generated `README`, package manifests,
and CI. Resolve contradictions in favor of executable project metadata and measured results. Run
the narrowest meaningful check first, then the full required set.

For a failed recorded check:

1. report its command, portable cwd, timeout, exit, and redacted detail;
2. inspect the first actionable project error;
3. preserve successful files and phases;
4. fix only when the user asked for repair;
5. rerun the exact failed command; and
6. update the handoff with measured results, not the earlier dashboard claim.

## Provider failure classes

- Missing binary: show current official installation guidance, then rerun doctor.
- Needs login: show the provider-owned login command from doctor; never handle credentials.
- Preflight required: explain that installation is not authenticated readiness.
- Model unavailable: remove the explicit override or use a provider-supported value.
- Quota/rate limit: preserve output and advise waiting, plan review, or another ready provider.
- Network: preserve partial output and check connectivity/proxy before retrying.
- Permission denied: retain safe mode; adjust a scoped provider policy or ask before unsafe mode.
- Timeout: preserve partial output and rerun only the failed command/phase with a justified limit.
- Unknown: report provider, exit, redacted tail, target, and the exact safe retry path.

## Privacy receipt

The final handoff may include project-relative paths, provider names, versions, non-identifying auth
modes, commands, exits, durations, and redacted failures. Do not include credentials, provider
account identity, organization identity, absolute home/workspace paths, full prompts, convention
contents, `.env` values, or raw provider transcripts unless the user explicitly approves that
boundary.
