# ProjectForge Showcase Evidence

This directory keeps portfolio claims tied to commands another reviewer can rerun. It separates
measured behavior from release work and from AI-generated output that requires an external
backend.

## Evidence bundle

- [verification-report.md](verification-report.md) records the clean GitHub install, CLI checks,
  dry run, package metadata, formula checksum, lint, build, and test results.
- [generated-project/](generated-project/) is a compact, locally verifiable example of the project
  shape used by the terminal demo.
- [terminal-demo.sh](terminal-demo.sh) performs the public install, prompt preview, authenticated
  scaffold, and artifact checks without deleting or overwriting an existing directory.
- [terminal-demo-shot-list.md](terminal-demo-shot-list.md) defines a truthful 30–60 second capture.

The example starts as a review fixture rather than a claimed AI-backend result. Run
`terminal-demo.sh` with an operator-approved backend to create the real manifest and terminal
capture; update this evidence only from that captured result.

## Independently verifiable proof points

1. A fresh uv tool directory installs the `projectforge` distribution from the immutable
   `Schramm2/projectforge@v0.4.1` release and exposes `forge`.
2. `forge --version`, `forge --help`, and a credential-free `--dry-run` work from that isolated
   installation.
3. The repository's public-safety scan, Ruff checks, package build, and full pytest suite are
   reproducible from the commands in the report.
4. The checked-in example has its own install, lint, test, and CLI checks and does not require
   network access at runtime.

## Claim boundary

- Measured outputs are dated and recorded in the verification report.
- Live scaffold quality depends on the selected external AI CLI and its authentication.
- `--demo` controls generated application credentials; it does not authenticate the AI CLI.
- PyPI and Homebrew are not supported public channels yet.
- The current public destination is <https://github.com/Schramm2/projectforge>. The final GitHub
  homepage and portfolio destination should be <https://mattschramm.com/work/projectforge> after
  that case study is live.
