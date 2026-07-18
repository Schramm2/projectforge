# Security and Privacy

ProjectForge launches an AI provider CLI on your machine. Review the boundary before a live run.

## What leaves your machine

For live generation, Forge sends the assembled project brief, effective conventions, explicitly
selected nearby Markdown, design or media context, and phase instructions to the chosen provider
through that provider's installed CLI. Nearby context discovery checks only a bounded set of known
filenames in the current folder. Forge includes none of their content until you select files in the
questionnaire. Selected files are limited to 32 KB each and 64 KB together and are secret-scanned
before prompt assembly. The provider's terms, retention policy, account configuration, and billing
apply.

`--dry-run` starts no provider process and makes no model call. `--export` also avoids provider
calls, but the exported prompt can contain private conventions and should be handled accordingly.

Forge does not collect provider credentials or account identity. Provider login remains inside the
provider-owned CLI. `forge doctor` reports only readiness and a non-identifying authentication mode
when the provider exposes one.

Normal doctor checks make no model call. For Antigravity, Forge runs `agy models`; this is an
authenticated model-catalog request, not an inference prompt. Forge uses only its exit status and
whether a non-empty catalog was returned, and does not retain catalog output or account identity.

During live execution, Forge uses provider output transiently to derive bounded activity summaries
and failure categories. It does not persist or echo raw provider output, stack traces, or captured
failure tails. A failing post-scaffold hook also suppresses both output streams and points you back
to the local hook for diagnosis; successful hook output is still shown in the terminal.

## Execution modes

- `--approval-mode safe` is the default. It maps to each provider's bounded workspace-write mode.
- `--approval-mode plan` is read-only provider planning.
- `--approval-mode unsafe --allow-unsafe` disables provider approval or sandbox boundaries. Use it
  only inside an external isolation boundary you control. Forge never selects it implicitly.

Safe mode still authorizes the provider to create and edit files inside the target workspace, run
commands there, install dependencies, use network access allowed by the provider, and consume
provider quota. Inspect the preflight panel and use `--no-open` when editor launch is unwanted.

Antigravity safe mode passes `--mode accept-edits --sandbox` to `agy --print`. Its sandbox applies
terminal restrictions; its permission engine and default disabled non-workspace access govern file
scope. Unapproved commands may be denied in non-interactive print mode. Only Forge's explicit
unsafe mode adds `--dangerously-skip-permissions` and removes the sandbox flag.

Generated code is untrusted until its recorded and independent checks pass. A successful provider
exit alone is not verification.

## Local data

Forge stores user configuration and local learning data under `~/.forge/`. Config writes are atomic
and user-readable only. Corrupted config is preserved with a timestamped `.corrupt-*` suffix.

Generated projects may contain:

- `.forge/progress.json` — prompt hashes and resumable phase state, never prompt content;
- `.forge/scaffold.json` — requested facts, routing, approval mode, and convention provenance;
- `.forge/conventions-snapshot.md` — exact effective conventions; treat it as potentially private;
- `.forge/context-snapshot.md` — approved project brief and selected nearby content, when supplied;
  treat it as potentially private;
- `.forge/verification.json` — redacted commands, exits, timeouts, endpoints, and remediation; and
- `.forge/card.svg` — the generated project card.

`~/.forge/scaffold.log`, quality signals, and preferences stay local. The scaffold log records only
the target directory name, not its absolute path. Forge redacts credential-shaped values from
progress and durable verification evidence, but secret scanning is defense in depth: never put
credentials in project briefs, nearby context files, descriptions, extra instructions, conventions,
exported prompts, or generated fixtures.

Post-scaffold hooks are user-authored shell code and run with your account's permissions. Review
`~/.forge/hooks/post-scaffold.sh` before enabling it.

## Recovery and reporting

On a provider failure, keep the partial project. Fix the classified provider problem, then repeat
the original command with `--resume`. Forge validates the recorded contract and skips completed
phases. Do not attach raw provider transcripts, convention snapshots, `.env` files, or credential
output to a public issue.

For ordinary bugs and support requests, use [GitHub Issues](https://github.com/Schramm2/projectforge/issues).
For a vulnerability, follow [SECURITY.md](../../SECURITY.md).
