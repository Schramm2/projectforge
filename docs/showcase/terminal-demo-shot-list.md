# Terminal Demo Shot List

Target: 30–60 seconds of legible terminal video using a real, authenticated backend.

1. Start with a clean terminal and show `FORGE_BACKEND` without exposing tokens or configuration.
2. Run `docs/showcase/terminal-demo.sh /tmp/projectforge-terminal-demo`.
3. Hold on the `projectforge` install and `forge --version` output.
4. Show the dry-run routing plan and prompt header; do not scroll through private conventions.
5. Show the live phase timeline. Trim waiting time only; keep the command and completion sequence
   contiguous so the edit cannot imply a different result.
6. Hold on the verification dashboard and the final `Verified scaffold` line.
7. End with `.forge/scaffold.json` and the generated README visible. Redact nothing except secrets;
   if secrets appear, discard the capture and fix the demo environment.

Record the date, ProjectForge commit, backend name, and generated manifest alongside the final
media. Do not claim the generation duration is 30–60 seconds; that is the edited video length and
backend runtime varies.
