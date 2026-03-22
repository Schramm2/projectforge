# Troubleshooting

## "No AI CLI tools found"

**Cause:** Forge requires at least one of `claude`, `gemini`, or `codex` on your PATH.

**Fix:** Install one or more:

- **Claude Code:** follow the [official setup guide](https://docs.anthropic.com/en/docs/claude-code), typically `npm install -g @anthropic-ai/claude-code`
- **Gemini CLI:** follow the [official repository README](https://github.com/google-gemini/gemini-cli), typically `npm install -g @google/gemini-cli`
- **Codex:** follow the [official repository README](https://github.com/openai/codex), typically `npm install -g @openai/codex`

Verify with:

```bash
which claude
which gemini
which codex
```

## "forge: command not found"

**Cause:** The `forge` binary is not on your PATH.

**Fix by install method:**

- **Homebrew:** Run `brew list ubundiforge` to confirm it is installed. If missing, run `brew tap matthewubundi/tap && brew install ubundiforge`.
- **From source:** Either activate the virtual environment or run directly with `./forge` from the repo root.

## Setup wizard keeps running

**Cause:** The config file is missing or corrupted, so Forge triggers setup on every launch.

**Fix:** Delete the config and re-run setup cleanly:

```bash
rm ~/.forge/config.json
forge --setup
```

## Scaffold fails mid-generation

**Cause:** The AI CLI subprocess crashed, timed out, or returned an error.

**Fix:**

1. Re-run with verbose output to see the full subprocess log:
   ```bash
   forge --verbose
   ```
2. Try a different backend:
   ```bash
   forge --use gemini
   ```
3. Verify the prompt is well-formed:
   ```bash
   forge --dry-run
   ```
4. Check that the AI CLI works independently (e.g., run `claude` directly in your terminal).

## "git init failed"

**Cause:** Git is not installed or not on PATH.

**Fix:** Install git from [git-scm.com](https://git-scm.com) or via your package manager. Verify with:

```bash
which git
git --version
```

## Post-scaffold hook not running

**Cause:** The hook file is missing, not executable, or exceeds the timeout.

**Checklist:**

1. File exists at `~/.forge/hooks/post-scaffold.sh`.
2. File is executable: `chmod +x ~/.forge/hooks/post-scaffold.sh`.
3. Script exits within 60 seconds. Long-running tasks should be backgrounded or moved to a separate script.

Test the hook manually:

```bash
FORGE_PROJECT_DIR=/tmp/test FORGE_PROJECT_NAME=test FORGE_STACK=fastapi FORGE_DEMO_MODE=0 bash ~/.forge/hooks/post-scaffold.sh
```

## Shell completions not working

**Cause:** The completion script is missing or the completion cache is stale.

**Fix (zsh):**

```bash
forge --install-completion
exec zsh
```

If you want to manage the script manually, export it and place it on your `fpath`:

```bash
mkdir -p ~/.zfunc
forge --show-completion > ~/.zfunc/_forge
fpath=(~/.zfunc $fpath)
autoload -Uz compinit && compinit
```

## Corrupted config

**Cause:** `~/.forge/config.json` contains invalid JSON, usually from a crash during setup.

**Fix:** Delete and regenerate:

```bash
rm ~/.forge/config.json
forge --setup
```
