# Provider Compatibility

Evidence date: 2026-07-18
Forge baseline: 0.4.1 at `1691b2d`

This ledger records what ProjectForge may safely assume about each supported AI CLI. Provider
documentation changes independently of Forge, so runtime help/version/status output is evidence
only for the tested version. Account identity and credential values are deliberately excluded.

## Support policy

- Installation and authentication belong to the provider. Forge may launch or explain official
  flows, then recheck status; it must never collect, parse, copy, log, or persist credentials.
- Installation is not authentication. Unknown readiness is not success.
- Omit `--model` by default so the provider can select its supported default/auto behavior.
- Explicit models are advanced overrides. Prefer stable aliases and let the provider validate the
  value at execution when no deterministic capability API exists.
- Use bounded workspace modes by default. Blanket bypass/yolo flags require a deliberately named
  unsafe mode and informed consent.
- A single ready provider is sufficient. Missing optional providers must not block scaffolding.

## Compatibility matrix

| Provider | Local evidence | Authentication status | Default model behavior | Safe non-interactive baseline | Dangerous escape hatch |
| --- | --- | --- | --- | --- | --- |
| Claude Code | 2.1.214 | `claude auth status`; JSON `loggedIn=true`, auth method recorded without identity | Omit `--model`; Claude settings/default apply. Stable aliases include `sonnet`, `opus`, and `haiku` | `claude -p --permission-mode acceptEdits --no-session-persistence <prompt>` with workspace permissions/settings constrained by the provider | `--permission-mode bypassPermissions` / `--dangerously-skip-permissions` |
| Codex CLI | 0.144.0 installed; 0.144.5 probed through the official latest npm package | `codex login status`; exit 0 and auth mode only | Omit `--model`; Codex uses the configured/recommended model | `codex --ask-for-approval never --sandbox workspace-write exec --cd <workspace> <prompt>`; `--json` and `--output-last-message` are available for inspection | `--dangerously-bypass-approvals-and-sandbox` / `--yolo`, only in an externally hardened environment |
| Google Antigravity CLI | 1.1.4 installed | `agy models`; exit 0 with a non-empty catalog confirms the provider-owned Google session without an inference prompt | Omit `--model`; Antigravity uses the current session default | `agy --mode accept-edits --sandbox --print <prompt>`; unapproved commands may be denied in print mode | `--dangerously-skip-permissions` without `--sandbox`, only with explicit unsafe consent |

ProjectForge now maps its provider-neutral modes as follows: `safe` uses Claude `acceptEdits`,
Codex `workspace-write` with non-interactive denial, and Antigravity `accept-edits` plus terminal
sandboxing; `plan` uses each provider's read-only mode; `unsafe` uses the provider bypass behavior
and is rejected unless the caller also supplies explicit unsafe consent. The installed provider
parsers accepted their generated safe/read-only command shapes without a model call on 2026-07-18.

## Claude Code

### Official sources

Retrieved 2026-07-18:

- <https://code.claude.com/docs/llms.txt>
- <https://code.claude.com/docs/en/setup>
- <https://code.claude.com/docs/en/authentication>
- <https://code.claude.com/docs/en/cli-usage>
- <https://code.claude.com/docs/en/permissions>

### Installation and authentication

Officially documented install routes include the recommended native installer, Homebrew casks,
WinGet, Linux package managers, and the global npm package. Forge should show the platform-relevant
official command and link rather than installing silently.

Interactive authentication is provider-owned. The tested runtime exposes `claude auth status` and
`claude auth login`. Forge may inspect the status result for readiness but must retain only a
boolean/unknown state and a non-identifying auth-method label.

### Invocation, models, permissions, and exits

- `-p` / `--print` is the documented non-interactive entry point.
- `--output-format` accepts text, JSON, or stream JSON; `--json-schema` supports validated final
  output on current versions.
- `--model` accepts stable aliases or a full model name. Forge defaults to omission.
- Permission modes include `default`/`manual`, `acceptEdits`, `plan`, `auto`, `dontAsk`, and
  `bypassPermissions`. `acceptEdits` permits edits and common filesystem operations inside the
  working directory/additional directories; `plan` is read-only; `dontAsk` denies unapproved
  tools; bypass skips most prompts but retains limited provider circuit breakers.
- `--allowedTools`, `--disallowedTools`, settings, and provider sandbox rules can further constrain
  execution. Forge must capability-detect the version it invokes.
- `--no-session-persistence` avoids saving print-mode sessions and is appropriate for Forge runs
  unless resume behavior is deliberately implemented through provider sessions.
- The current runtime help describes failures through non-zero exits. Forge must classify stderr
  and retain a redacted tail rather than assuming every non-zero exit means authentication.

Known limitation: a safe non-interactive write run still needs a permission mode that can complete
without an interactive approval prompt. Forge must test and document the effective workspace
boundary; it must refuse if the selected mode cannot complete safely and unattended behavior was
not explicitly authorized.

## Codex CLI

### Official sources

Retrieved 2026-07-18:

- <https://developers.openai.com/codex/cli/reference>
- <https://developers.openai.com/codex/auth>
- <https://developers.openai.com/codex/security>
- <https://developers.openai.com/codex/models>
- <https://github.com/openai/codex>

The developers.openai.com URLs currently redirect to the official ChatGPT Learn documentation.

### Installation and authentication

Official install routes include the native install script, npm, Homebrew cask, and platform
binaries from GitHub releases. Authentication supports ChatGPT sign-in, API key, and access-token
flows. `codex login status` prints the active authentication mode and exits 0 when credentials are
present; Forge should use the exit code plus a non-identifying mode classification.

### Invocation, models, sandboxing, and exits

- `codex exec` is the scripted/CI entry point and accepts a prompt argument or stdin.
- `--cd` sets the workspace root. `--add-dir` expands write access and should be avoided unless a
  user explicitly adds a required directory.
- `--sandbox` accepts `read-only`, `workspace-write`, or `danger-full-access`. Official guidance
  recommends `workspace-write` for unattended local work that remains inside the workspace.
- Global `--ask-for-approval` values are `untrusted`, `on-request`, and `never`. Current
  non-interactive behavior needs runtime validation in combination with the selected sandbox.
- `--json` emits JSONL progress and `--output-last-message` writes the final response, enabling
  inspectable redacted failure handling.
- `--model` overrides the configured model. If no model is configured, the CLI uses a recommended
  model; Forge defaults to omission.
- `--full-auto` is deprecated in current official docs in favor of explicit
  `--sandbox workspace-write`.
- `--dangerously-bypass-approvals-and-sandbox` disables both boundaries and is documented only for
  an isolated/external sandbox. Forge must never select it implicitly.

Known limitation: authentication evidence applies to the installed 0.144.0 runtime. The official
latest npm package reported 0.144.5 and accepted the relevant version/help surface in an isolated
probe, but it was not given access to host authentication and made no model call.

## Google Antigravity CLI

### Official sources

Retrieved 2026-07-18:

- <https://antigravity.google/docs/cli-overview>
- <https://antigravity.google/docs/cli-install>
- <https://antigravity.google/docs/cli-using>
- <https://antigravity.google/docs/cli/modes>
- <https://antigravity.google/docs/cli/permissions>
- <https://github.com/google-antigravity/antigravity-cli>

### Installation and authentication

The official installer places `agy` under the user's local binary directory. On first launch,
Antigravity uses an existing system-keyring session or opens Google Sign-In. SSH sessions print an
authorization URL and accept the returned code in the terminal. `/logout` clears the provider-owned
session.

`agy models` is a bounded readiness check: an authenticated session returns the available model
display names, while an unauthenticated clean profile exits non-zero and asks the user to launch
`agy` to sign in. Forge uses only the exit and non-empty-result condition, and never retains model
catalog output, account identity, authorization codes, or credentials.

### Invocation, models, policies, and exits

- `--print` / `-p` runs one prompt non-interactively. Keep it as the final flag immediately before
  the prompt because the Go parser treats it as value-taking.
- `--model` overrides the session model. Forge omits it by default and lets Antigravity select its
  current default.
- `--mode accept-edits` automatically approves file edits and creations. `--mode plan` uses
  read-only investigation tools and produces a plan.
- `--sandbox` enables terminal restrictions. It is not the file-permission engine; workspace and
  non-workspace file access remain governed by Antigravity permissions and settings.
- Print mode cannot answer interactive permission prompts. Current versions deny unapproved tools
  with guidance rather than granting them. Users can allow narrowly scoped commands in
  `/permissions`; Forge does not edit the user's global settings.
- `--dangerously-skip-permissions` auto-approves tool requests and is used only by Forge's explicit
  unsafe mode. Forge omits `--sandbox` in that mode so its risk is not disguised.

Known limitation: a safe headless scaffold can write workspace files but may be unable to run a
command that the user's Antigravity policy has not already allowed. Forge preserves the provider
failure and independently verifies generated output rather than silently escalating permissions.

## Runtime evidence, 2026-07-18

- Claude Code 2.1.214 accepted the generated safe and plan command surfaces. Its provider-owned
  status command reported authenticated through Claude.ai; Forge retained no identity.
- The installed Codex CLI 0.144.0 accepted the generated safe and plan command surfaces. Its
  provider-owned status command reported authenticated through ChatGPT; Forge retained no identity.
- The official latest Codex npm package reported 0.144.5 and exposed the required `exec`, sandbox,
  approval, model, JSON, and final-message options in a clean no-install probe.
- Antigravity CLI 1.1.4 reported its version, exposed `--print`, `--model`, `--mode`, `--sandbox`,
  and `--dangerously-skip-permissions`, and returned its model catalog through the saved Google
  session. The same `agy models` command in a clean isolated home exited non-zero with provider-owned
  sign-in guidance and did not open a browser.
- All probes above were version/help/status-only. They made no model calls and recorded no account
  identifier, credential, token, or provider response body.

## Failure taxonomy

Forge should map provider output and exit behavior into these stable user-facing classes while
retaining a redacted diagnostic summary:

| Class | Evidence | Recovery |
| --- | --- | --- |
| Missing binary | Executable lookup fails | Show official install link/command, then rerun doctor |
| Unauthenticated | Documented status is false/non-zero or provider explicitly requests login | Launch or show provider-owned auth flow, then rerun doctor |
| Check inconclusive | A bounded status command times out or returns an unclassified error | Check connectivity/keyring access and rerun the provider-owned status command |
| Unavailable model | Provider rejects explicit model/alias | Remove the override or choose a provider-supported alias |
| Quota/rate limit | Provider emits a rate/quota class response | Preserve output; wait, change provider, or review plan/billing |
| Network | DNS, connection, TLS, or provider-unreachable failure | Check connectivity/proxy and retry without changing project output |
| Permission denied | Provider approval/policy/sandbox refusal | Keep the safe mode; adjust scoped policy or explicitly choose unsafe mode |
| Timeout | Forge deadline expires and process is terminated | Preserve output and phase state; resume/retry with a documented timeout |
| Unknown provider failure | Non-zero exit not matched above | Show provider, exit, redacted tail, workspace, and rerun guidance |

## Remaining live evidence

- Run an isolated bounded-write probe with a current-stable authenticated provider.
- Run a bounded Antigravity workspace-write scaffold and record which commands require explicit
  scoped permission rules in print mode.
- Run bounded Claude and Codex failure probes for permission/model/network classification where
  they can be done without secrets or external side effects.
- Complete at least one authenticated end-to-end Forge scaffold and independently verify every
  generated check before publication.
