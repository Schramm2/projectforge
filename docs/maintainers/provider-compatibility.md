# Provider Compatibility

Evidence date: 2026-07-19
Forge baseline: v0.7.1 working source

The runtime evidence below is a bounded smoke-test record, not a guarantee that a provider's
independent CLI contract will remain unchanged.

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
| Claude Code | 2.1.215 | `claude auth status`; JSON `loggedIn=true`, auth method recorded without identity | Omit `--model`; provider default applies | `claude --safe-mode -p --permission-mode acceptEdits --no-session-persistence <prompt>` | `--permission-mode bypassPermissions` / `--dangerously-skip-permissions` |
| Codex CLI | 0.144.6 | `codex login status`; exit 0 and auth mode only | Omit `--model`; provider default applies | `codex --cd <workspace> --ask-for-approval never --sandbox workspace-write exec --skip-git-repo-check --ephemeral --ignore-user-config --color never <prompt>` | `--dangerously-bypass-approvals-and-sandbox` / `--yolo`, only in an externally hardened environment |
| Google Antigravity CLI | 1.1.4 | `agy models`; exit 0 with a non-empty catalog confirms the provider-owned Google session without an inference prompt | Omit `--model`; current session default applies | `agy --add-dir <workspace> --mode accept-edits --sandbox --print <prompt>` with a Forge-managed, temporary `write_file(<workspace>)` allow rule for headless writes | `--dangerously-skip-permissions` without `--sandbox`, only with explicit unsafe consent |

ProjectForge maps its provider-neutral modes as follows: `safe` uses Claude `safe-mode` plus
`acceptEdits`, Codex `workspace-write` with the git-repo-check bypassed, ephemeral execution, and
ambient user config ignored, and Antigravity `add-dir` plus `accept-edits` and terminal sandboxing; `plan` uses each provider's
read-only mode; `unsafe` uses the provider bypass behavior and is rejected unless the caller also
supplies explicit unsafe consent. Antigravity is the exception: safe workspace writes need a
headless `write_file` allow rule, which Forge grants temporarily and scoped to the workspace for the
duration of the run.

## Claude Code

### Official sources

Retrieved 2026-07-19:

- <https://code.claude.com/docs/en/cli-usage>
- <https://code.claude.com/docs/en/setup>
- <https://code.claude.com/docs/en/authentication>
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
- `--safe-mode` disables ambient hooks, skills, plugins, MCP, memory, and project `CLAUDE.md`
  discovery while preserving the provider's normal authentication path. Forge supplies its
  effective conventions and project instructions in the prompt.
- `--no-session-persistence` avoids saving print-mode sessions and is appropriate for Forge runs
  because Forge owns resume state separately.
- The current runtime help describes failures through non-zero exits. Forge classifies captured
  output transiently and presents a bounded category and recovery step; it does not echo or
  persist the captured provider tail.

Known limitation: a safe non-interactive write run still needs a permission mode that can complete
without an interactive approval prompt. Forge must test and document the effective workspace
boundary; it must refuse if the selected mode cannot complete safely and unattended behavior was
not explicitly authorized.

## Codex CLI

### Official sources

Retrieved 2026-07-19:

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
- `--cd` sets the workspace root. Forge passes the target explicitly even though it also sets the
  subprocess cwd.
- `--sandbox` accepts `read-only`, `workspace-write`, or `danger-full-access`. Official guidance
  recommends `workspace-write` for unattended local work that remains inside the workspace.
- Global `--ask-for-approval` values are `untrusted`, `on-request`, and `never`. Current
  non-interactive behavior needs runtime validation in combination with the selected sandbox.
- `--json` emits JSONL progress and `--output-last-message` writes the final response. Forge keeps
  text output transient so it can derive bounded activity and failure categories without creating a
  second durable transcript.
- `--skip-git-repo-check` is required. Forge scaffolds into a fresh directory and only runs
  `git init` as a post-scaffold step, so during generation the target is not a git repo. Without
  this flag `codex exec` refuses to start with "not inside a trusted directory", which breaks every
  safe and plan scaffold.
- `--ephemeral` prevents Codex exec rollout/session files from being persisted. `--ignore-user-config`
  keeps ambient user configuration and exec rules from changing Forge's explicit policy; official
  docs state that authentication still uses `CODEX_HOME`.
- `--color never` avoids terminal decoration in the transient stream Forge summarizes.
- `--model` overrides the configured model. If no model is configured, the CLI uses a recommended
  model; Forge defaults to omission.
- `--full-auto` is deprecated in current official docs in favor of explicit
  `--sandbox workspace-write`.
- `--dangerously-bypass-approvals-and-sandbox` disables both boundaries and is documented only for
  an isolated/external sandbox. Forge must never select it implicitly.

The installed 0.144.6 runtime accepted the explicit workspace, git-repo-check bypass, ephemeral,
ambient-config, color, sandbox, approval, model, and exec flags. A real bounded smoke call into a
fresh non-git directory wrote the requested file and left no provider sidecar; the same call without
`--skip-git-repo-check` aborts before any turn with "not inside a trusted directory".

## Google Antigravity CLI

### Official sources

Retrieved 2026-07-19:

- <https://antigravity.google/docs/cli-overview>
- <https://antigravity.google/docs/cli-install>
- <https://antigravity.google/docs/cli-using>
- <https://antigravity.google/docs/cli/projects>
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

- `--add-dir <workspace>` binds the target to the Antigravity workspace. Without it, a print-mode
  call can use the provider's own scratch project even when Forge sets the subprocess cwd.
- `--print` / `-p` runs one prompt non-interactively. Keep it as the final flag immediately before
  the prompt because the Go parser treats it as value-taking.
- `--model` overrides the session model. Forge omits it by default and lets Antigravity select its
  current default.
- `--mode accept-edits` automatically approves file edits and creations. `--mode plan` uses
  read-only investigation tools and produces a plan.
- `--sandbox` enables terminal restrictions. It is not the file-permission engine; file access is
  governed by Antigravity's permission rules.
- Print mode cannot answer interactive permission prompts. Official permissions documentation says
  unconfigured actions default to Ask, so safe headless file writes require a narrow
  `write_file(<workspace>)` entry under `~/.gemini/antigravity-cli/settings.json`. For the duration
  of a safe-mode run Forge adds exactly that rule (merging non-destructively), then restores the
  file to its prior state; see `src/projectforge/provider_permissions.py`.
- `--dangerously-skip-permissions` auto-approves tool requests and is used only by Forge's explicit
  unsafe mode. Forge omits `--sandbox` in that mode so its risk is not disguised.

Forge's scoped `write_file(<workspace>)` grant covers the common safe scaffold. As a safety net, if
a write is still denied (for example a command the policy blocks, or a settings file Forge cannot
write), Antigravity may report the denied tool as exit 0; Forge recognizes the headless permission
message and fails the phase rather than advancing with no workspace change. Explicit unsafe mode is
the only path that adds `--dangerously-skip-permissions`.

## Runtime evidence, 2026-07-19

- Claude Code 2.1.215 reported an authenticated Claude.ai session. A real `run_ai` safe-mode smoke
  call created the requested file in the target and did not create the ambient `.code-review-graph/`
  sidecar observed with the uncontained command.
- Codex CLI 0.144.6 reported an authenticated ChatGPT session. A real `run_ai` smoke call into a
  fresh non-git target using explicit `--cd`, `--skip-git-repo-check`, `--ephemeral`,
  `--ignore-user-config`, and `--color never` created the requested file and left no provider
  sidecar. The identical call without `--skip-git-repo-check` aborts before any turn with "not
  inside a trusted directory", which is the state every scaffold hits before Forge's post-scaffold
  `git init`.
- Antigravity CLI 1.1.4 reported an authenticated Google session. Without `--add-dir`, a print-mode
  call wrote to the provider scratch project rather than the Forge target. With `--add-dir` but no
  allow rule, safe print mode was denied because headless mode could not answer the missing
  `write_file` permission; the provider still exited 0, and Forge converts that response into a
  `permission` failure. With Forge's temporary workspace-scoped `write_file` rule, a real `run_ai`
  safe-mode call wrote the target file and exited 0, and Forge restored the settings file to its
  prior absence afterward.
- These live probes used bounded smoke prompts in disposable temporary workspaces (fresh non-git
  directories, matching real scaffolds). No provider account identifier, credential, token, or raw
  response was recorded in Forge evidence.

## Readiness and execution failure vocabulary

Forge maps provider output and exit behavior into stable user-facing classes without echoing or
persisting the captured output:

| Class | Evidence | Recovery |
| --- | --- | --- |
| `missing_binary` | Executable lookup fails | Run `forge doctor` for setup steps, then retry with `--resume` |
| `authentication` | Provider output indicates missing or invalid sign-in | Run `forge doctor`, complete its provider-owned sign-in step, then retry with `--resume` |
| `model` | Provider rejects an explicit model | Remove `--model` to use the provider default, then retry with `--resume` |
| `quota` | Provider output indicates a usage, rate, credit, or billing limit | Preserve the partial project, wait for access to return, then retry with `--resume` |
| `network` | Provider output indicates DNS, connection, proxy, or reachability failure | Check the connection and proxy, run `forge doctor`, then retry with `--resume` |
| `permission` | Provider approval, sandbox, or workspace policy blocks the step | Keep safe mode, review scoped workspace access, then retry with `--resume` |
| `timeout` | Forge terminates a phase after its deadline | Preserve the partial project and retry the incomplete work with `--resume` |
| `unknown` | Non-zero exit does not match a known pattern | Preserve completed work, run `forge doctor`, then retry with `--resume` |

Doctor readiness uses a separate status vocabulary. In particular, `check_inconclusive` means the
bounded provider-owned status check did not prove ready or signed out; it is not an execution
failure category and must not be treated as successful readiness.

## Remaining live evidence

- Repeat a bounded Antigravity safe smoke call through Forge's real `run_ai` path and confirm both
  the target output and that Forge restored `~/.gemini/antigravity-cli/settings.json` to its prior
  state afterward.
- Complete one authenticated end-to-end scaffold per provider before publishing a release that
  claims full generated-project compatibility; these probes validate CLI execution, not stack
  quality or verification behavior.
