# Public Release Checklist

Use this checklist before treating ProjectForge as fully public-ready. These items require
repository or release-channel decisions outside the codebase.

- Rename or move the current personal-owner, legacy-branded repository to a neutral
  ProjectForge repository name and owner.
- Update the GitHub repository description, topics, homepage URL, and social preview after
  the rename.
- Choose the final Homebrew tap owner/name, then replace `<tap-owner>/<tap>` placeholders in
  install docs and configure `HOMEBREW_TAP_REPO`.
- Regenerate `Formula/projectforge.rb` with the final public release tarball URL and checksum.
- Replace `<repository-url>` placeholders in source-install docs once the public repository
  URL is final.
- Run a separate git history scan before declaring the repository fully privacy-clean; the
  tracked working tree scanner does not inspect historical commits, reflogs, forks, or hosted
  release artifacts.
- Confirm release metadata before publishing to package indexes or Homebrew.
