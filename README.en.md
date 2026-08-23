# Bilibili Video to Learning Notes

[简体中文](README.md) | [English](README.en.md)

Turn Bilibili videos into **subtitle-first Obsidian learning notes**.

Send a Bilibili URL or BV ID. The project collects available Chinese subtitles, the uploader's original description, and video metadata, then lets an agent extract the useful knowledge, write the note, review coverage, and publish it to Obsidian.

The default workflow **does not download video or audio**.

> First-time users should start with the [Quick Start guide](docs/QUICKSTART.md). The detailed operational documentation is currently maintained in Chinese.

---

## What it does

The normal workflow is:

```text
Bilibili URL / BV ID
→ collect subtitles, description, and metadata
→ prepare long transcripts
→ agent extracts knowledge
→ write a concise summary + structured learning content
→ finalizer validates the result
→ publish to Obsidian
```

It is designed for:

- tutorials, courses, and technical videos on Bilibili;
- AI, ComfyUI, programming, and other knowledge-dense content;
- people who want searchable and reviewable notes instead of a watch-history backlog;
- workflows where a link is sent from a phone and processed by a local agent on a computer.

The project currently provides entry points for **Hermes, WorkBuddy, and Codex**. They share the same collector, transcript preparation, taxonomy, note rules, and finalizer.

---

## Key features

- Accepts BV IDs, standard Bilibili URLs, copied text containing a BV ID, and supported `b23.tv` short links.
- Uses `yt-dlp --skip-download`; media is not downloaded in the default path.
- Preserves the uploader's original description and useful resource links.
- Conservatively recognizes explicit resource-access conditions such as likes/favorites/coins, charging, comment keywords, direct messages, or group access. It never invents a template or file that was not present in the source material.
- Stops when the available source is insufficient instead of filling factual gaps from model knowledge.
- Converts long subtitles into a transcript manifest and ordered chunks so agents do not need to load an entire long SRT at once.
- Uses the lightweight writing flow by default: read the full transcript, write the note directly, then run a separate layout pass. A strict auditable flow remains available.
- Merges tiny trailing transcript chunks to avoid wasteful extra reads.
- Publishes new notes to `00-待整理` first; knowledge organization is a separate post-learning step.
- Uses the original video title as the filename and adds `（2）`, `（3）`, etc. instead of overwriting an existing note.
- Generates deterministic metadata, resource sections, tags, CSS classes, paths, and filenames in code rather than asking the LLM to rewrite them.
- Publishes only after the finalizer returns `note_ready`.
- Keeps Cookie contents out of logs, notes, and Git.

---

## Requirements

For a normal Windows setup you need:

| Requirement | Purpose |
| --- | --- |
| Python 3.10+ | Runs the core package and adapter scripts |
| yt-dlp | Collects metadata, descriptions, and subtitles |
| Bilibili Cookie file | Usually required for authenticated subtitle/metadata access |
| Obsidian Vault or Markdown destination | Stores generated notes |
| Hermes, WorkBuddy, or Codex | Reads the prepared transcript and writes the knowledge sections |

The project does not bundle `yt-dlp.exe` and does not install it automatically.

On Windows, if `yt-dlp` is not already available in `PATH`:

```powershell
winget install yt-dlp
```

---

## Installation

Clone the repository:

```powershell
git clone https://github.com/ZiYao00/bili-learning-automation.git
cd bili-learning-automation
```

For normal Hermes / WorkBuddy usage, the core runtime has no third-party Python package dependency.

For development and testing:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

---

## Configuration

The recommended machine-local configuration is:

```text
config/local.json
```

Copy the example first:

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

Where:

- `vault_root` is the Obsidian Vault directory that directly contains `.obsidian`;
- `notes_subdir` is the relative directory used by this project inside the Vault;
- `cookie_file` points to a Netscape-format Bilibili Cookie file;
- `workflow_mode` is `light` by default; use `strict` to restore the staged Fact Ledger / Semantic Draft / Layout Plan workflow.

`config/local.json` is ignored by Git.

You may also use environment variables:

- `BILI_LEARNING_TAXONOMY`
- `BILI_LEARNING_VAULT_ROOT`
- `BILI_LEARNING_NOTES_SUBDIR`
- `BILI_LEARNING_NOTES_ROOT` (legacy compatibility)
- `BILI_LEARNING_YTDLP`
- `BILI_LEARNING_COOKIE_FILE`
- `BILI_LEARNING_WORKFLOW_MODE` (`light` / `strict`)

See [Configuration](docs/CONFIGURATION.md) for the full behavior and precedence rules.

---

## Run the environment check

Before the first real conversion, run:

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

For structured output:

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

The doctor checks Python, taxonomy, note/runtime write access, Vault configuration, Obsidian CSS, yt-dlp, Cookie-file presence, and required project documents.

It does **not** read Cookie contents and does **not** access Bilibili.

---

## Obsidian styling

The repository includes:

```text
obsidian/snippets/
├── learning-lab.css
└── video-note.css
```

Copy both files to:

```text
<vault_root>/.obsidian/snippets/
```

Then enable both snippets in:

```text
Obsidian → Settings → Appearance → CSS snippets
```

`video-note.css` extends `learning-lab.css`, so both should be enabled.

See [Obsidian Styling](docs/OBSIDIAN-STYLING.md).

---

## Agent entry points

| Agent | Typical use | Adapter |
| --- | --- | --- |
| Hermes | Send a Bilibili link from a private chat / phone workflow | `hermes-skills/bili-learning-automation/` |
| WorkBuddy | Convert links inside a WorkBuddy session | `workbuddy-skills/bili-learning-automation/` |
| Codex | Development, testing, and direct project maintenance | Read `AGENTS.md`, then follow the selected `workflow_mode` |

These are thin adapters. The project intentionally keeps the content and validation rules in a shared core rather than maintaining separate implementations for each agent.

---

## Daily usage

After installation and configuration, send a supported agent either:

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

or:

```text
BVxxxxxxxxxx
```

The agent should handle collection, transcript preparation, source sufficiency checks, knowledge extraction, coverage review, finalization, and publication automatically.

---

## Long videos

Long subtitles are prepared under the current runtime job:

```text
.runtime/bilibili-learning/<job>/agent-work/
├── transcript-manifest.json
└── transcript/
    ├── transcript-01.txt
    ├── transcript-02.txt
    └── ...
```

Chunking preserves subtitle order and complete cue boundaries. It is a transport mechanism for the agent, not a semantic summary or keyword filter.

Runtime files are temporary and are cleaned by the finalizer / failsafe path.

---

## Note output

New notes are first published to:

```text
<notes_root>/00-待整理/
```

The primary reading order is:

```text
Title / author · date · duration · BV ID
→ Key takeaways
→ Video resources
   → Bilibili player
   → Compact resource-access instructions when explicitly present
   → Compact uploader-resource links
   → Compact video overview + folded raw description
→ Learning content
```

The resource section is intentionally compact: there is no extra “Original video” heading, resource links are grouped, and the full uploader description remains folded. For dense encyclopedia-style videos, the agent first builds an atomic fact ledger before the final outline/body and must re-check the original transcript before marking coverage as passed, reducing semantic compression of values, member relationships, exceptions, and compatibility details.

After you have actually studied a note, the separate organization flow can shorten the title, add a one-line description, suggest a taxonomy category, move the file safely, and rebuild navigation.

---

## Common statuses

| Status | Meaning |
| --- | --- |
| `configuration_required` | No explicit Obsidian Vault has been bound yet; collection does not start |
| `materials_ready` | Subtitle/description materials are prepared for the agent |
| `in_progress` | An active job already exists for the same BV ID |
| `subtitle_unavailable` | No usable Chinese subtitle was obtained |
| `source_insufficient` | The available source is insufficient for a reliable learning note |
| `note_ready` | Finalizer validation passed and the note was published |
| `note_invalid` | The draft failed final validation |
| `failed` | Configuration, collection, or runtime processing failed |

`in_progress` is a concurrency safeguard, not a permanent deduplication rule. The same video can be converted again after the active job is finished.

---

## Privacy and local data

The following are ignored by Git by default:

- Cookie files;
- private notes;
- `.runtime` jobs;
- machine-local `config/local.json`;
- archives and temporary materials;
- virtual environments and test caches.

Do not paste Cookie contents into issues, logs, example configuration, or agent conversations.

Do not manually remove active runtime jobs, reservations, or lock files, and do not bypass the finalizer to publish an unfinished draft.

See [Security](SECURITY.md).

---

## Development and tests

```powershell
python -m compileall -q src hermes-skills/bili-learning-automation/scripts
python -m ruff check .
python -m pytest -q
```

Public tests do not require a real Cookie and should not access a real Bilibili account.

CI runs on Windows and Linux with Python 3.10 and 3.12.

See [Development](docs/DEVELOPMENT.md).

---

## Legacy path

`hermes-skills/bili-learning-automation/scripts/prepare_bilibili_learning.py` belongs to the older Chrome/CDP + `bili-note` + `web-access` workflow and is not the default entry point.

New integrations should use the yt-dlp subtitle-first flow.

See [Legacy](docs/LEGACY.md).

---

## Documentation

The detailed documentation is currently maintained in Chinese:

- [Quick Start](docs/QUICKSTART.md)
- [Configuration](docs/CONFIGURATION.md)
- [Hermes Skill Installation](docs/HERMES-SKILL-INSTALL.md)
- [WorkBuddy Skill Installation](docs/WORKBUDDY-SKILL-INSTALL.md)
- [Obsidian Styling](docs/OBSIDIAN-STYLING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Agent Integration Protocol](docs/AGENT-INTEGRATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development](docs/DEVELOPMENT.md)
- [v1.0 Release Checklist](docs/RELEASE-CHECKLIST.md)

---

## License

This project is licensed under [PolyForm Noncommercial 1.0.0](LICENSE). Personal study, research, testing, hobby projects, and other noncommercial uses are permitted under the license; commercial use is outside the granted scope.

Third-party dependencies remain subject to their own licenses.
