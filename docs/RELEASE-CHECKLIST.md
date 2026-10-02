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
- [x] yt-dlp is detected rather than silently bundled or installed.
- [x] Cookie contents are excluded from logs, notes, examples, and Git by design.
- [x] ChatGPT, Codex, Hermes, and WorkBuddy share the same core workflow and content rules.
- [x] Chinese README and beginner documentation are present.
- [x] English README is present as a public project overview.
- [x] Repository license wording is consistent with `LICENSE`.
- [x] Ruff passes in the existing project virtual environment.
- [x] Public pytest suite passes.
- [x] Source, shared launchers, and canonical Skill bridge scripts compile successfully.
- [x] `skill/bili-learning-automation/SKILL.md` is the single maintained local Skill source; Codex/Hermes/WorkBuddy use user-level Junctions to that directory, and `build_chatgpt_skill.py --check` validates the only distributable Skill ZIP. The ChatGPT archive contains only the generated Skill metadata and approved documentation reference snapshot, with no local credentials or machine configuration.
- [x] Fresh-install / clean-room walkthrough rerun after the 2026-08-22 dense-note extraction and compact-template corrections; see `docs/reports/2026-08-23-v1.0-cleanroom-acceptance.md`.
- [ ] `pyproject.toml` version matches the intended release version before tagging.
- [ ] Changelog contains the final release entry/date for that version.
- [x] Final diff review confirms no local credentials, private notes, runtime jobs, captured test materials, or machine-specific configuration are staged.
- [x] Public tracked documentation contains no maintainer-specific absolute paths, Vault/backup locations, private identifiers, or machine-only examples; generic placeholders are used instead.
- [ ] Git author/committer identity for the release commit uses an email address the maintainer intentionally wants to expose publicly (for privacy, prefer a GitHub `noreply` address when appropriate).
- [x] Older public commits that contained an unintended private email were separately reviewed and rewritten before this release candidate; the public refs were revalidated before promotion.
- [ ] CI is green on the exact commit selected for the release tag.
- [ ] The GitHub Release for the intended version is created from that verified commit.

---

## Clean-room walkthrough

The final manual acceptance test should simulate a new user rather than an experienced maintainer.

Use a fresh clone or otherwise isolated checkout and verify only the documented path:

1. Clone the repository.
2. Confirm `config/local.json` does not already exist.
3. Follow `docs/QUICKSTART.md` without relying on remembered local setup.
4. Copy `config/local.json.example` to `config/local.json`; configure a Git-ignored `notes_root`, test Vault/Cookie path, and create the Vault → `notes_root` Junction when testing the recommended hybrid topology.
5. Run doctor/onboarding before doing a real collection and confirm `obsidian_notes_mapping` is OK in hybrid mode.
6. Confirm missing yt-dlp produces installation guidance rather than an automatic install attempt.
7. Confirm an unconfigured note/Vault location returns `configuration_required` and does not start collection; a broken hybrid Junction must return `obsidian_notes_mapping_invalid`.
8. Install/enable both Obsidian CSS snippets and confirm doctor recognizes them.
9. Install one supported agent entry point using its documented instructions.
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
2. Fix only release-blocking defects or documentation mismatches found by that walkthrough.
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
