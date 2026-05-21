# GitHub Copilot Instructions

Use these repository-specific conventions when proposing branches, labels, and version changes.

## Branch naming

- Use `feature/<short-description>` or `feat/<short-description>` for new user-facing functionality.
- Use `fix/<short-description>` or `bugfix/<short-description>` for bug fixes and regressions.
- Use `docs/<short-description>` for documentation-only work.
- Use `chore/<short-description>` for maintenance changes that do not change user-facing behavior.
- Use `deps/<short-description>` for dependency or automation updates.
- Use `release/<major>.<minor>` or `release/<major>.<minor>.<patch>` only for release preparation branches.

Prefer lowercase branch names with hyphen-separated descriptions, for example `feature/add-stop-alerts` or `fix/hacs-metadata-version`.

## Labels and PR intent

Match branch names and PR intent to the labels defined in `.github/labels.yml`:

- `feature` or `enhancement`: new capabilities or meaningful improvements.
- `fix`, `bugfix`, or `bug`: defect fixes.
- `documentation`: README, docs, or translation/documentation-only changes.
- `chore`: maintenance and repo upkeep.
- `dependencies`: dependency or workflow/tooling updates.
- `major`: breaking changes or intentional major-release work.
- `skip-changelog`: only when the PR should be excluded from release notes.

When a branch prefix maps cleanly to a label, prefer that prefix so automation and reviewers can infer intent quickly.

## Version increments

This repository uses semantic versioning in `custom_components/transit_departures/manifest.json`.

- Increment the major version for breaking changes or PRs labeled `major`.
- Increment the minor version for `feature` and `enhancement` changes.
- Increment the patch version for `fix`, `bugfix`, `bug`, `chore`, `documentation`, and `dependencies` changes.

These rules should stay aligned with `.github/release-drafter.yml`.

## Version bump rules

- Do not bump the version number on every code change by default.
- Bump the version only when explicitly preparing a release or when asked to do so.
- When bumping the version, update `custom_components/transit_departures/manifest.json` first.
- Release tags must match the manifest version and use the format `vX.Y.Z`.
- If release metadata depends on the integration version, keep it consistent with the manifest version.

## Pull requests

- Target `main` unless the user explicitly asks for another base branch.
- Use a concise PR title that reflects the release label intent, for example `Fix HACS metadata parsing` or `Release 0.2.1`.
- Keep release-preparation PRs scoped to release-related changes only.
