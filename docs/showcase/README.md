# ProjectForge Showcase Evidence

This directory ties portfolio claims to reproducible commands and measured results.

## Evidence bundle

- [verification-report.md](verification-report.md) is the dated historical v0.4.1 release and live
  scaffold record.
- [generated-project/](generated-project/) is a deterministic local fixture with its own install,
  lint, test, and CLI checks. It is not presented as the authenticated live result.
- [terminal-demo.sh](terminal-demo.sh) installs the current checkout in isolation, previews the
  prompt, runs a real backend, and independently checks the generated project. Set `FORGE_SOURCE`
  to an immutable archive URL to capture a specific release instead.
- [terminal-demo-shot-list.md](terminal-demo-shot-list.md) defines a truthful 30–60 second edit from
  the real terminal capture.

## Independently verifiable proof points

1. The historical report proves that a fresh uv tool directory installed v0.4.1 from its immutable
   GitHub archive and exposed `forge`.
2. The historical report proves that the public Homebrew tap installed and tested v0.4.1 from
   source.
3. The repository safety scan, Ruff checks, package build, and full pytest suite pass.
4. A real Claude-backed `python-cli` scaffold completed all three phases; its independent Ruff,
   pytest, mypy, and CLI checks pass.
5. The portfolio case study is live on the default Vercel project URL without a custom domain.

## Claim boundary

- Measured outputs are dated in the historical verification report; they are not claims about the
  current unreleased source.
- Live scaffold quality and runtime depend on the external AI CLI and its authentication.
- `--demo` controls generated application credentials; it does not authenticate the AI CLI.
- PyPI is deliberately unpublished and is not an install route.
- The canonical project destination remains
  <https://github.com/Schramm2/projectforge>; portfolio evidence is available at the Vercel case
  study URL recorded in the report.
- No custom domain is attached or required.
