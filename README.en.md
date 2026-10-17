# Bilibili Video to Learning Notes

[简体中文](README.md) | [English](README.en.md)

**Current code version: v2.0.1 (local release candidate; GitHub Release pending)**

`bili-learning-automation` converts Bilibili subtitles, explicitly authorized ASR text, or explicitly requested description-only resource information into Obsidian notes.

The default `prepare` route is subtitle-first and uses `yt-dlp --skip-download`, so **video and audio are not downloaded**. After subtitles are unavailable, explicitly authorized `prepare-asr` checks for existing notes before calling the independent ASR service; `prepare-transcript` imports the resulting text, while `prepare-description` is used only when the current request explicitly asks for a pure resource / description-only note. All three routes share one Job lifecycle, validation, publication, recovery, concurrency protection, and retire flow.

> First installation: start with **[Quick Start](docs/QUICKSTART.md)**.
> The detailed operating documentation is currently maintained in Chinese and is Windows-first.

---

## 1. Purpose

Normal flow:

```text
Bilibili URL / BV ID
→ choose subtitle_srt / asr_text / description_only from the current explicit request
→ create one source manifest; subtitle / ASR may be chunked, description-only has no fabricated chunks
→ Agent checks whether the allowed source is sufficient
→ write key takeaways + note content
→ re-check coverage against the allowed source
→ finalizer validates the draft
→ publish to Obsidian / 00-待整理
→ retire the runtime job from the active task area
```

The note format is intended to retain useful source information such as:

- parameters, values, formulas, and limits;
- models, nodes, plugins, LoRAs, and versions;
- steps and prerequisites;
- A/B differences, compatibility, and conflicts;
- timing, quality changes, and failure behavior from tests;
- GitHub repositories, models, workflows, and other uploader resources;
- limitations, risks, and selection conditions stated by the source.

Factual content is limited to the source mode selected for the current Job:

- `subtitle_srt`: current subtitles, uploader description, any deterministically collected uploader-pinned top-level comment, and explicitly supplied user material;
- `asr_text`: explicitly authorized ASR text, uploader description, any collected uploader-pinned top-level comment, and explicitly supplied user material;
- `description_only`: title, metadata, uploader description, any collected uploader-pinned top-level comment, and explicitly supplied user material, without inferring speech or visual facts from the uncollected video.

If those materials are too incomplete to support a reliable note, the Agent may return `source_insufficient` instead of filling specific facts from model knowledge.

---

## 2. Requirements

Windows 10/11 x64, Python 3.10+, an Obsidian vault, a private Netscape-format Bilibili cookie file, and at least one local-capable agent (Codex, Hermes, WorkBuddy, or ChatGPT with an authorized local workspace bridge). Python and `.venv` are **not** shipped with the repository: an authorized Agent runs `scripts/run_bili_learning.ps1 -ProbeOnly` first and, only with permission, installs Python 3.12 if required.

The repository bundles the **official standalone `tools/yt-dlp.exe`**; all runtime calls use that fixed path exclusively. No yt-dlp source installation, global PATH search, or `winget` install is needed. Release provenance and SHA-256 are recorded in `tools/yt-dlp.release.json`. Subtitle-first collection uses `--skip-download` and does not download media.

`local-ASR-service` is an **optional, independent** tool. Its current default local endpoint is `127.0.0.1:8191` (configurable via local settings or environment override). It is never installed or started by this project and is only used after explicit user authorization for ASR.

## 3. Installation: ask your agent

There is no double-click installer. Ask an authorized local agent to read `AGENTS.md`, `docs/QUICKSTART.md`, and `docs/LOCAL-AGENT-INSTALL.md`, then check prerequisites, install the canonical Skill, configure Obsidian and the cookie-file path, and confirm the structured `onboarding` result. Existing directories and links must not be overwritten without authorization.

The included PowerShell helpers (`scripts/install_agent_skill.ps1`, `scripts/ensure_junction.ps1`) **only plan by default**. The agent must secure permission for the specific external location before invoking `-Apply`. ChatGPT Web also requires a separate Skill ZIP and a permitted local-workspace bridge.

See the [Agent-first Quick Start](docs/QUICKSTART.md), [Local Agent setup](docs/LOCAL-AGENT-INSTALL.md), and [ChatGPT Skill setup](docs/CHATGPT-SKILL-INSTALL.md). Most detailed operating documentation is maintained in Chinese.

---

## 4. Daily usage

Send a supported Agent either:

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

or:

```text
BVxxxxxxxxxx
```

Supported copied Bilibili text and supported `b23.tv` short links can also be used.

Routing depends only on the current explicit request:

```text
Convert this link                              → default subtitle-first route
Pure resource note; description only; no subs  → description_only
(after subtitle_unavailable) run ASR and continue → asr_text
```

The project does not skip subtitles merely because the title looks like a preview/resource post, and it does not use historical memory to select a source mode.

All three source routes check published notes by BVID before collection. If that BVID already exists, the default behavior is to ask whether to update an existing note, rerun as a new note, or cancel. Update preserves the selected note path and stores a runtime snapshot plus SHA-256 guard; rerun creates a separate note and only then uses `（2）`, `（3）`, and later suffixes for a same-title collision.

Normally you do not need to manually:

- download subtitles;
- split long transcripts;
- choose the output filename;
- choose the `00-待整理` path;
- edit runtime job files.

New notes are first published to:

```text
<notes_root>/00-待整理/
```

After the user explicitly chooses rerun, a same-title collision creates `（2）`, `（3）`, and so on instead of overwriting an existing note. Update keeps the selected existing path and filename.

---

## 5. Note structure

The normal reading order is:

```text
Title
Author · published date · duration · BVID

Key takeaways

Bilibili player
Uploader resources / access conditions / description / raw source

Learning content
```

The learning body does not use a fixed chapter count. The Agent chooses headings, tables, steps, lists, and callouts according to the current source.

Subtitle / ASR sources may contain speech-to-text noise. If a model name, plugin name, or another proper noun cannot be confirmed, preserve uncertainty rather than turning model memory into a source fact. Description-only has no audio source and must not be used to infer speech.

---

## 6. Writing modes

### `light` - default

```text
read the current allowed source through the source manifest
→ source-sufficiency check
→ write the note directly (description-only remains a concise resource note)
→ separate layout pass
→ coverage re-check against the allowed source
→ finalizer
```

This is the normal daily mode.

### `strict` - optional

Adds:

```text
Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Plan
→ Source Recheck
```

It is mainly intended for debugging knowledge loss, auditing intermediate stages, and quality regressions.

Most users should keep `light`.

---

## 7. Agents and models

The project is **not tied to a specific LLM**. Only `skill/bili-learning-automation/SKILL.md` is maintained by hand. Codex, Hermes, and WorkBuddy point their user-level Skill directories directly at that canonical source through Junctions; the repository no longer generates host-specific local copies. `scripts/build_chatgpt_skill.py` builds the only distributable Skill ZIP for ChatGPT Web and adds a safe documentation-reference snapshot. Source collection, Source Mode, source manifests, taxonomy, content rules, validation, and finalization remain shared.

Model differences can affect:

- long-context understanding;
- parameter and proper-noun fidelity;
- reconstruction of relationships between alternatives;
- retention of experimental evidence;
- writing and information organization.

The project uses fixed-video quality regressions, but the README does not maintain a permanent model ranking because model versions, Agent hosts, proxy backends, pricing, and capabilities change.

---

## 8. Common statuses

| Status | Meaning | Normal action |
| --- | --- | --- |
| `onboarding_required` | First-run setup still lacks a required Vault / Cookie / yt-dlp item | Handle the returned `actions`, re-check, and retry the original link |
| `materials_ready` | A standard Job for the selected `source_mode` is ready | Continue through `source_manifest_path` and the handoff; `recovered: true` means the core resumed a complete Job for the same source mode |
| `existing_note_found` | A published note already has the same BVID | Stop before collection and ask: update, rerun, or cancel; preserve the original full message when retrying |
| `update_target_required` | Multiple notes share the BVID and no update target was selected | Ask the user to choose the exact note; do not guess latest/oldest |
| `update_conflict` | The update target changed after the Job started | Do not overwrite it; report the conflict and start a fresh update if requested |
| `in_progress` | Another task is still genuinely active for the same BVID | Do not start a duplicate collection or manually alter runtime state |
| `subtitle_unavailable` | No usable Chinese subtitle was obtained | Stop this conversion |
| `source_insufficient` | The selected source mode is insufficient for a reliable note | Use fuller subtitle/ASR text, or add description material / switch away from description-only |
| `note_ready` | Finalizer passed and the note was published | Business flow is complete; runtime retire/maintenance state does not change the publish result |
| `note_invalid` | Draft failed final validation | Fix the reported issue; do not bypass finalizer |
| `failed` | Configuration, collection, or runtime failure | Run doctor, then use Troubleshooting |

The core can recover a complete job left by a dead process and rebuild a missing handoff. Normal locks, reservations, and job lifecycle no longer depend on delete permission. See [Troubleshooting](docs/TROUBLESHOOTING.md) for detailed diagnosis.

---

## 9. Privacy and local data

These are ignored by Git by default:

```text
key/                 # Cookie / local credentials
notes/**             # private learning notes; physical Markdown may live in the repo workspace but stays ignored
config/local.json    # machine-specific paths
.runtime/            # active / retired runtime jobs
```

The public repository should contain only generic examples and empty directory placeholders such as `config/local.json.example`, `key/.gitkeep`, and `notes/.gitkeep`, not machine-local configuration or private notes.

See [SECURITY.md](SECURITY.md).

---

## 10. Documentation

Detailed documentation is currently maintained in Chinese.

### Tutorials

- [Quick Start](docs/QUICKSTART.md)
- [Bilibili Cookie setup and security](docs/BILIBILI-COOKIE.md) (Chinese)
- [ChatGPT Skill Installation](docs/CHATGPT-SKILL-INSTALL.md)
- [Local Agent Skill Installation](docs/LOCAL-AGENT-INSTALL.md) for Codex, Hermes, and WorkBuddy
- [Obsidian Styling](docs/OBSIDIAN-STYLING.md)
- [Post-learning Filing (rename/move only)](docs/NOTE-ORGANIZATION.md)

### Reference

- [Configuration](docs/CONFIGURATION.md)
- [Dependencies](docs/DEPENDENCIES.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Agent Integration Protocol](docs/AGENT-INTEGRATION.md)
- [Maintenance Handoff](docs/MAINTENANCE-HANDOFF.md) for a new Agent or maintainer taking over the project

### Troubleshooting and safety

- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Security](SECURITY.md)

### Development

- [Development](docs/DEVELOPMENT.md)
- [Release Checklist](docs/RELEASE-CHECKLIST.md)

---

## 11. Development and tests

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

Public tests do not require a real Cookie and should not access a real Bilibili account.

---

## 12. License

This project uses [PolyForm Noncommercial 1.0.0](LICENSE).

Personal learning, research, testing, and other non-commercial use are allowed. Commercial use is outside the scope of the current license. Third-party dependencies remain subject to their own licenses.
