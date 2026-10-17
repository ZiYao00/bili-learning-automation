# Release Checklist

This document defines the reusable pre-release and pre-push gate for `bili-learning-automation`. Version-specific acceptance reports remain under `docs/reports/`.

Use this checklist whenever preparing a commit that will be pushed publicly or promoted to a Release. During an explicit release freeze, limit changes to release-blocking fixes, documentation corrections, packaging/version metadata, security fixes, and verification work.

---

## Release criteria

A release candidate is ready when all applicable checks below are true:

- [x] Core workflow is stable in normal daily use.
- [x] Default collection path does not download video or audio.
- [x] Subtitle-first source policy and source-insufficiency guard are implemented.
- [x] Long transcript preparation and tiny-tail merge behavior are covered by tests.
- [x] Finalizer is the only successful publication gate.
- [x] New notes do not overwrite existing notes with the same title.
- [x] Obsidian storage supports the recommended hybrid topology: physical `notes_root` in Git-ignored project storage plus a Vault Junction mapping, while repository fallback remains protected.
- [x] Windows x64 project bundles only official single-file `tools/yt-dlp.exe`; collector and ASR use that path exclusively (no PATH / env / local override). SHA-256, release provenance, and bundled third-party licenses are tracked in `tools/`.
- [x] Cookie contents are excluded from logs, notes, examples, and Git by design.
- [x] ChatGPT, Codex, Hermes, and WorkBuddy share the same core workflow and content rules.
- [x] Chinese README and beginner documentation are present.
- [x] English README is present as a public project overview.
- [x] Repository license wording is consistent with `LICENSE`.
- [x] Ruff passes in the existing project virtual environment.
- [x] Public pytest suite passes.
- [x] Source, shared launchers, and canonical Skill bridge scripts compile successfully.
- [x] Windows Python preflight is available without a Python interpreter; launcher and canonical Skill bridge validate the same Python 3.10+ interpreter. Missing Python never silently installs or opens the Store; unsupported/broken `.venv` is not trusted. A real no-Python host remains part of clean-room acceptance.
- [x] `skill/bili-learning-automation/SKILL.md` is the single maintained local Skill source; Codex/Hermes/WorkBuddy use user-level Junctions to that directory, and `build_chatgpt_skill.py --check` validates the only distributable Skill ZIP. The ChatGPT archive contains only the generated Skill metadata and approved documentation reference snapshot, with no local credentials or machine configuration.
- [x] Historical clean-room walkthrough completed in August 2026; see `docs/reports/2026-08-23-v1.0-cleanroom-acceptance.md`.
- [x] Isolated Windows clean-room simulation passed: a copied workspace without `.venv`, private config or Cookie can use an explicitly validated external Python, configure Vault and Cookie path, install Junction safely, and return onboarding `ready`; repeated install and occupied targets remain non-destructive.
- [ ] Repeat **independent** Agent-led installation on a genuinely fresh Windows 10/11 x64 host (including no-Python handling, explicit OS-install authorization, real Agent discovery, and a permissioned Bilibili smoke run). Local isolated simulation does not count as this separate release gate.
- [ ] Confirm Linux CI uses deterministic fake executable tests rather than treating the Windows EXE as Linux-supported.
- [x] `pyproject.toml` local candidate version is `2.0.1`, and both READMEs and CHANGELOG agree. This is a local candidate, not a pushed tag or GitHub Release; the prior `v2.0.0` Git tag already exists.
- [x] CHANGELOG includes the `2.0.1` candidate with date `2026-10-17`; reconfirm the actual release date immediately before creating the tag.
- [ ] For the next release commit, review full staged paths and verify no local credentials, private notes, runtime jobs, captured materials, or machine-specific configuration are staged. Current read-only review is not a staged release gate.
- [x] Public tracked documentation contains no maintainer-specific absolute paths, Vault/backup locations, private identifiers, or machine-only examples; generic placeholders are used instead.
- [ ] Git author/committer identity for the release commit uses an email address the maintainer intentionally wants to expose publicly (for privacy, prefer a GitHub `noreply` address when appropriate).
- [x] Older public commits that contained an unintended private email were separately reviewed and rewritten before this release candidate; the public refs were revalidated before promotion.
- [ ] CI is green on the exact commit selected for the release tag.
- [ ] The GitHub Release for the intended version is created from that verified commit.

---

## Clean-room walkthrough

The final manual acceptance test should simulate a new user rather than an experienced maintainer.

Use a fresh clone or otherwise isolated checkout and verify only the documented path:

1. With an authorized Agent, clone or download the repository in a fresh Windows 10/11 x64 environment.
2. Confirm `config/local.json` does not already exist; never import the maintainer's private config.
3. The Agent follows `docs/QUICKSTART.md` without remembered local settings or manual JSON edits by the novice user.
4. Run `scripts/run_bili_learning.ps1 -ProbeOnly` **before** any Python CLI command; exercise no-Python and incompatible-Python branches, then use a validated Python 3.10+ or an explicitly authorized official Python 3.12 install. Confirm `tools/yt-dlp.exe --version` runs, version and SHA-256 match `tools/yt-dlp.release.json`, and no global yt-dlp lookup occurs.
5. Agent configures the Vault and Cookie **file path** using shared CLI. New hybrid installations must create workspace notes root safely and plan Vault → notes Junction; only apply after external target permission.
6. Verify `scripts/ensure_junction.ps1` returns `planned` on read-only inspection, `installed` on permitted creation, `already_installed` on a repeat, and `conflict` on an occupied unrelated target; never remove existing data.
7. Run doctor/onboarding through `scripts/run_bili_learning.ps1` before any real collection; missing EXE, Vault, Cookie or broken hybrid mapping must report structured actions without collecting media. Verify Chinese/space-containing paths, valid external Python without a local `.venv`, and invalid interpreter selection.
8. Confirm missing CSS is a non-blocking warning; only copy from its upstream project with permission.
9. Agent installs only one selected host Skill through `scripts/install_agent_skill.ps1` plan/apply; confirm the host can read canonical SKILL.md. ChatGPT Web requires separate ZIP and authorized workspace bridge.
10. Convert one normal Bilibili video with usable Chinese subtitles.
11. Confirm the note lands in `00-待整理` and the original video title is preserved as the filename.
12. Convert the same video again after the first job is complete and confirm the existing note is not overwritten.
13. Confirm the generated note contains the expected metadata, summary/body structure, video resources, uploader description, and any source-supported conditional resource instructions.
14. Confirm the finalizer reports `note_ready` before treating the task as successful.
15. Confirm the successful Job leaves the active runtime area and is retired safely; physical deletion is not a business-success requirement.
16. Confirm no Cookie content appears in logs, notes, Git diff, or generated examples.

A failure in steps 3-16 is a release blocker if it prevents the documented default workflow or violates the stated security/data boundary.

---

## Final release sequence

Do not add features during this sequence.

1. Complete the clean-room walkthrough.
2. Fix only release-blocking defects or documentation mismatches found by that walkthrough; if the version candidate date differs from the actual release date, synchronize CHANGELOG and metadata before tagging.
3. Set `pyproject.toml` to the intended release version.
4. Add the final `## [X.Y.Z] - YYYY-MM-DD` changelog entry for that version.
5. Run:

```powershell
python -m compileall -q src scripts skill/bili-learning-automation/scripts
python -m ruff check .
python -m pytest -q
python .\scripts\build_chatgpt_skill.py
python .\scripts\build_chatgpt_skill.py --check
git -c core.whitespace=cr-at-eol diff --check
```

6. Review the complete Git diff and staged file list for credentials and local-only data.
7. Push the release commit and require CI to pass.
8. Tag that exact commit with the intended version (for example `vX.Y.Z`) and create the GitHub Release.

---

## What should usually wait until the next minor release

Unless required to fix a release blocker, defer these categories until a later release:

- new video platforms;
- new agent platforms or large adapter redesigns;
- automatic ASR/media-download fallback;
- new LLM provider abstractions;
- Web UI or desktop UI;
- major taxonomy redesign;
- new note-layout systems;
- unrelated CSS redesign;
- speculative performance optimization without a reproduced problem.

For any release candidate, stability, reproducibility, documentation, and data safety take priority over feature count.
