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
| Gemini CLI | No global binary; 0.51.0 version/help probed through the official no-install route | No documented deterministic status command; installation remains unknown/preflight-required until an explicit model preflight succeeds | CLI default is `auto`; omit `--model` | `gemini --prompt <prompt> --approval-mode auto_edit --sandbox` only after an explicit readiness preflight | `--approval-mode yolo`; deprecated `--yolo` / `-y` |

ProjectForge now maps its provider-neutral modes as follows: `safe` uses Claude `acceptEdits`,
Codex `workspace-write` with non-interactive denial, and Gemini `auto_edit` plus sandboxing; `plan`
uses each provider's read-only mode; `unsafe` uses the provider bypass/yolo behavior and is rejected
unless the caller also supplies explicit unsafe consent. The installed Claude and Codex parsers
accepted their generated safe/read-only command shapes without a model call on 2026-07-18.

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

## Gemini CLI

### Official sources

Retrieved 2026-07-18:

- <https://geminicli.com/docs/>
- <https://geminicli.com/docs/get-started/installation/>
- <https://geminicli.com/docs/get-started/authentication/>
- <https://geminicli.com/docs/cli/cli-reference/>
- <https://geminicli.com/docs/cli/model/>
- <https://geminicli.com/docs/reference/policy-engine/>

### Installation and authentication

Official stable install routes include npm, Homebrew, MacPorts, and an npm install inside an
Anaconda environment; `npx @google/gemini-cli` is the documented no-install route. Authentication
supports Google sign-in, Gemini API key, and Vertex AI variants. Headless mode uses an existing
cached credential or provider environment variables.

The official authentication and CLI references expose no safe deterministic login-status command.
Therefore Forge must report an installed Gemini CLI as `unknown/preflight-required`, not ready.
The explicit verification path is `forge doctor --preflight gemini`, after completing the
provider-owned authentication flow. It makes one sentinel-only call in a temporary workspace using
plan mode, sandboxing, and JSON output. A success stores only the CLI version and verification
timestamp with a 24-hour lifetime and owner-only permissions; provider output is not persisted.

### Invocation, models, policies, and exits

- `--prompt` / `-p` forces non-interactive mode; output can be text, JSON, or stream JSON.
- The CLI default model value is `auto`; Forge should omit `--model` and describe this as provider
  auto-selection.
- Approval modes are `default`, `auto_edit`, `yolo`, and `plan`; the policy-engine docs spell the
  internal names as `default`, `autoEdit`, `yolo`, and `plan`.
- `plan` is read-only. `default` prompts for most writes. `auto_edit` permits some automated edits.
  `yolo` auto-approves every tool and requires explicit unsafe consent.
- `--sandbox` requests a sandboxed environment. Forge must verify availability and failure behavior
  on the invoked version rather than assuming Docker/Podman support.
- `--yolo` / `-y` is deprecated in favor of `--approval-mode=yolo` and must be removed from normal
  Forge commands.

Known limitations: no global binary or authentication evidence exists; there is no official status
API; and a safe headless write preflight may consume quota. The official no-install route reported
0.51.0 and exposed the documented prompt, model, sandbox, approval-mode, and output-format options,
but no model call was made. Release evidence must label Gemini live validation unavailable until an
explicit preflight succeeds.

## Runtime evidence, 2026-07-18

- Claude Code 2.1.214 accepted the generated safe and plan command surfaces. Its provider-owned
  status command reported authenticated through Claude.ai; Forge retained no identity.
- The installed Codex CLI 0.144.0 accepted the generated safe and plan command surfaces. Its
  provider-owned status command reported authenticated through ChatGPT; Forge retained no identity.
- The official latest Codex npm package reported 0.144.5 and exposed the required `exec`, sandbox,
  approval, model, JSON, and final-message options in a clean no-install probe.
- The official latest Gemini npm package reported 0.51.0 and exposed prompt, model, sandbox,
  approval modes (`default`, `auto_edit`, `yolo`, and `plan`), and structured output in a clean
  no-install probe. Authentication and live write behavior remain unavailable evidence.
- All probes above were version/help/status-only. They made no model calls and recorded no account
  identifier, credential, token, or provider response body.

## Failure taxonomy

Forge should map provider output and exit behavior into these stable user-facing classes while
retaining a redacted diagnostic summary:

| Class | Evidence | Recovery |
| --- | --- | --- |
| Missing binary | Executable lookup fails | Show official install link/command, then rerun doctor |
| Unauthenticated | Documented status is false/non-zero or provider explicitly requests login | Launch or show provider-owned auth flow, then rerun doctor |
| Preflight required | Installed provider lacks deterministic status | Explain unknown state and offer an isolated minimal verification |
| Unavailable model | Provider rejects explicit model/alias | Remove the override or choose a provider-supported alias |
| Quota/rate limit | Provider emits a rate/quota class response | Preserve output; wait, change provider, or review plan/billing |
| Network | DNS, connection, TLS, or provider-unreachable failure | Check connectivity/proxy and retry without changing project output |
| Permission denied | Provider approval/policy/sandbox refusal | Keep the safe mode; adjust scoped policy or explicitly choose unsafe mode |
| Timeout | Forge deadline expires and process is terminated | Preserve output and phase state; resume/retry with a documented timeout |
| Unknown provider failure | Non-zero exit not matched above | Show provider, exit, redacted tail, workspace, and rerun guidance |

## Remaining live evidence

- Run an isolated bounded-write probe with a current-stable authenticated provider.
- Run Gemini's explicit opt-in readiness preflight when authentication is available; do not infer
  readiness from the successful 0.51.0 version/help probe.
- Run bounded Claude and Codex failure probes for permission/model/network classification where
  they can be done without secrets or external side effects.
- Complete at least one authenticated end-to-end Forge scaffold and independently verify every
  generated check before publication.
