# Bilibili Video to Learning Notes

[简体中文](README.md) | [English](README.en.md)

`bili-learning-automation` converts Bilibili subtitles, the uploader's original description, and video metadata into Obsidian learning notes.

The default pipeline uses `yt-dlp --skip-download`, so **video and audio are not downloaded**. An Agent reads the transcript and writes the learning content, while the program manages deterministic metadata, paths, validation, publication, concurrency protection, job recovery, and the runtime retire lifecycle.

> First installation: start with **[Quick Start](docs/QUICKSTART.md)**.
> The detailed operating documentation is currently maintained in Chinese and is Windows-first.

---

## 1. Purpose

Normal flow:

```text
Bilibili URL / BV ID
→ collect Chinese subtitles, uploader description, metadata
→ prepare transcript; chunk long subtitles when needed
→ Agent checks whether the current source is sufficient
→ write key takeaways + learning content
→ re-check transcript coverage
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

Factual content in the generated learning body is normally limited to:

- the current video's subtitles;
- the uploader's original description.

If those materials are too incomplete to support a reliable note, the Agent may return `source_insufficient` instead of filling specific facts from model knowledge.

---

## 2. Requirements

A normal Windows setup needs:

| Requirement | Purpose |
| --- | --- |
| Python 3.10+ | Runs the core scripts |
| yt-dlp | Collects subtitles, description, and metadata |
| Bilibili Cookie file | Provides an authenticated Bilibili browser session; required by the normal collection flow |
| Obsidian Vault | Stores generated learning notes |
| Hermes / WorkBuddy / Codex | Reads the transcript and writes the learning content |

The repository does not bundle or auto-install `yt-dlp.exe`.

```powershell
winget install yt-dlp
```

Cookie files are credentials. The project expects a complete Mozilla/Netscape `cookies.txt` file, not a single `SESSDATA` value. Configure a **file path**; do not paste Cookie contents into README files, issues, pull requests, logs, or Agent conversations. The detailed beginner guide is [Bilibili Cookie setup](docs/BILIBILI-COOKIE.md) (Chinese).

---

## 3. First installation

See [Quick Start](docs/QUICKSTART.md) for the full tutorial.

### 3.1 Clone

```powershell
git clone https://github.com/ZiYao00/bili-learning-automation.git
cd bili-learning-automation
```

### 3.2 Machine-local configuration

Normal users can let the Agent fill missing values during onboarding. If you prefer to maintain the local configuration manually, copy the template:

```powershell
Copy-Item .\config\local.json.example .\config\local.json
```

Example:

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt",
  "workflow_mode": "light"
}
```

`config/local.json` is ignored by Git and is intended for machine-specific paths.

### 3.3 Prepare the Bilibili Cookie file

Log into Bilibili in your browser and export a complete Mozilla/Netscape `cookies.txt` file. Do not copy only `SESSDATA`; yt-dlp expects the full Netscape cookie file. Store it as a private local file and configure only its path.

The detailed beginner tutorial covers browser export, format validation, `--cookies-from-browser` security considerations, Windows `Failed to decrypt with DPAPI`, and cookie renewal: [Bilibili Cookie setup and security](docs/BILIBILI-COOKIE.md) (Chinese).

### 3.4 First-run environment check

After connecting Hermes, WorkBuddy, or Codex, the Agent should run onboarding before the first real collection and only ask the user for values that cannot be detected automatically. You can run the same check manually:

```powershell
python .\hermes-skills\bili-learning-automation\scripts\onboarding_bilibili_learning.py
```

`action_required` returns only the missing user-facing setup items such as the Vault, Cookie file path, or yt-dlp. Missing CSS is a non-blocking warning. For the full diagnostic report, run:

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

Doctor checks Python, yt-dlp, Cookie-file presence, the Vault, CSS, taxonomy, write permissions, and required project files. It **does not read Cookie contents and does not access Bilibili**.

### 3.5 Install Obsidian styling

The project uses the shared [Obsidian Learning Snippets](https://github.com/ZiYao00/obsidian-learning-snippets) repository.

Install:

```text
learning-lab.css
video-note.css
```

into:

```text
.obsidian/snippets/
```

Then enable both snippets in Obsidian.

### 3.6 Choose an Agent entry point

| Agent | Typical use | Documentation |
| --- | --- | --- |
| Hermes | Send a Bilibili link from a phone / private chat | [Hermes installation](docs/HERMES-SKILL-INSTALL.md) |
| WorkBuddy | Send a link inside a WorkBuddy session | [WorkBuddy installation](docs/WORKBUDDY-SKILL-INSTALL.md) |
| Codex | Development, testing, direct project operation | Read `AGENTS.md` first |

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

If the same filename already exists, the project creates `（2）`, `（3）`, and so on instead of overwriting the existing note.

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

Bilibili subtitles may be speech-to-text output. If a model name, plugin name, or another proper noun cannot be confirmed, the content rules preserve uncertainty rather than silently turning model memory into a source fact.

---

## 6. Writing modes

### `light` - default

```text
read complete transcript
→ source-sufficiency check
→ write the note directly
→ separate layout pass
→ transcript coverage re-check
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

The project is **not tied to a specific LLM**. Hermes, WorkBuddy, and Codex are different entry points; collector, transcript preparation, taxonomy, content rules, validation, and finalization are shared.

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
| `materials_ready` | Subtitles, description, and metadata are ready | Agent continues; `recovered: true` means the core resumed a complete prior job without re-collecting |
| `in_progress` | Another task is still genuinely active for the same BVID | Do not start a duplicate collection or manually alter runtime state |
| `subtitle_unavailable` | No usable Chinese subtitle was obtained | Stop this conversion |
| `source_insufficient` | Current source is insufficient for a reliable note | Use a source with better text coverage |
| `note_ready` | Finalizer passed and the note was published | Business flow is complete; runtime retire/maintenance state does not change the publish result |
| `note_invalid` | Draft failed final validation | Fix the reported issue; do not bypass finalizer |
| `failed` | Configuration, collection, or runtime failure | Run doctor, then use Troubleshooting |

The core can recover a complete job left by a dead process and rebuild a missing handoff. Normal locks, reservations, and job lifecycle no longer depend on delete permission. See [Troubleshooting](docs/TROUBLESHOOTING.md) for detailed diagnosis.

---

## 9. Privacy and local data

These are ignored by Git by default:

```text
key/                 # Cookie / local credentials
config/local.json    # machine-specific paths
notes/**             # private learning notes
.runtime/            # active / retired runtime jobs
.codex-backups/      # local backups
archive/ materials/  # local materials
```

The public repository should contain generic examples such as `config/local.json.example`, not a user's machine-local configuration.

See [SECURITY.md](SECURITY.md).

---

## 10. Documentation

Detailed documentation is currently maintained in Chinese.

### Tutorials

- [Quick Start](docs/QUICKSTART.md)
- [Bilibili Cookie setup and security](docs/BILIBILI-COOKIE.md) (Chinese)
- [Hermes Skill Installation](docs/HERMES-SKILL-INSTALL.md)
- [WorkBuddy Skill Installation](docs/WORKBUDDY-SKILL-INSTALL.md)
- [Obsidian Styling](docs/OBSIDIAN-STYLING.md)
- [Post-learning Filing (rename/move only)](docs/NOTE-ORGANIZATION.md)

### Reference

- [Configuration](docs/CONFIGURATION.md)
- [Dependencies](docs/DEPENDENCIES.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Agent Integration Protocol](docs/AGENT-INTEGRATION.md)

### Troubleshooting and safety

- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Security](SECURITY.md)

### Development

- [Development](docs/DEVELOPMENT.md)
- [Release Checklist](docs/RELEASE-CHECKLIST.md)
- [Legacy](docs/LEGACY.md)

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
