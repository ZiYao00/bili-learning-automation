# Bilibili Video to Learning Notes

[简体中文](README.md) | [English](README.en.md)

Turn a Bilibili video link into a **durable, searchable Obsidian learning note**.

The project uses a **subtitle-first** workflow: by default it collects Chinese subtitles, the uploader's original description, and video metadata without downloading video or audio. An Agent then extracts knowledge, reviews coverage, writes the learning content, and hands the draft back to a deterministic finalizer for publication.

> **In one sentence:** this is not a “compress the video into a few bullets” tool. It tries to preserve parameters, versions, tools, steps, comparisons, failure cases, limitations, and useful resource links so the video becomes knowledge you can actually reuse later.

**License:** [PolyForm Noncommercial 1.0.0](LICENSE). Non-commercial use is allowed; commercial use is not granted by the current license.

> First-time users should start with the **[Quick Start](docs/QUICKSTART.md)**. The detailed operational documentation is currently maintained in Chinese and is Windows-first.

---

## Why this project exists

Tutorials and technical videos often contain much more value than a short summary can preserve:

- parameters, values, limits, and practical presets;
- models, nodes, plugins, LoRAs, versions, and installation prerequisites;
- A/B differences, compatibility, conflicts, and selection rules;
- timing, quality changes, failure behavior, and trade-offs from real tests;
- GitHub repositories, models, workflows, and other resources from the uploader description;
- capability boundaries: when a method is useful and when it is not.

`bili-learning-automation` is designed to **protect this reusable knowledge first**, rather than optimize for the shortest possible output.

---

## 30-second workflow

```text
Bilibili URL / BV ID
        ↓
yt-dlp collects subtitles, description, metadata
        ↓
prepare transcript / chunk long subtitles
        ↓
Agent checks whether the source is sufficient
        ↓
extract knowledge + write key takeaways and learning content
        ↓
re-check the transcript for coverage
        ↓
finalizer validates the draft
        ↓
publish to Obsidian / 00-待整理
```

The default collector uses `yt-dlp --skip-download`, so **video and audio are not downloaded**.

---

## How it differs from a normal video summarizer

### 1. It can stop when the source is not good enough

Factual content in the note may only come from:

- the current video's subtitles;
- the uploader's original description.

If subtitles are badly incomplete, critical details exist only on screen, or important terms are too damaged to support a reliable note, the Agent can return `source_insufficient` instead of filling gaps with model knowledge.

### 2. Long videos are not summarized before writing

Long subtitles are converted into an ordered transcript manifest and chunks. Chunking is only a transport mechanism for the Agent; it does not perform semantic summarization, keyword filtering, or early compression.

This lets 20-40 minute or longer technical videos retain parameters, relationships, experiments, and failure cases instead of collapsing into a few topic headings.

### 3. Uncertain proper nouns keep search clues without pretending certainty

Bilibili subtitles are often generated from speech. When model names, plugin names, or other proper nouns are mistranscribed:

- if the source confirms the name, use the confirmed form;
- if the name is strongly implied but not confirmable, keep the subtitle form and mark it as unconfirmed;
- if the name cannot be identified, preserve the useful role, parameters, relationships, and experiment results while omitting the spelling.

This avoids both extremes: losing an entire knowledge point because one word is wrong, or silently “correcting” the subtitle from model memory.

### 4. The LLM only owns the parts that require reasoning

The program generates deterministic content such as:

- Frontmatter;
- H1 and author/date/duration/BVID metadata;
- Bilibili player;
- uploader description and resource links;
- tags and CSS classes;
- filenames, paths, and overwrite protection;
- finalizer validation and runtime cleanup.

The Agent mainly writes two regions:

- **Key takeaways** for fast value judgment;
- **Learning content** organized around the actual information in the video.

### 5. New notes go to an inbox first

Every new note is first published to:

```text
00-待整理/
```

Only after you have actually studied it should the optional organization flow shorten the title, add a one-line description, suggest a taxonomy category, move the file safely, and rebuild navigation.

---

## What the generated note looks like

```text
Title
Author · published date · duration · BVID

Key takeaways

Bilibili player
Uploader resources / access conditions / original description

Dynamic learning content
├── parameters and configuration
├── comparisons
├── steps and prerequisites
├── experiments
├── failure cases
├── risks and limitations
└── other reusable knowledge from the source
```

There is no fixed five-section template and no target H2 count, word count, or file size. A simple video can stay short; an encyclopedia-style tutorial can be long.

The project uses the shared [Obsidian Learning Snippets](https://github.com/ZiYao00/obsidian-learning-snippets) visual system. The Markdown remains readable even when CSS is disabled.

---

## Good fits

This project is a strong fit for:

- Bilibili tutorials, courses, and technical walkthroughs;
- ComfyUI, AI, image/video generation, local models, programming, and other parameter-heavy content;
- people who want long-term reference notes instead of one-time summaries;
- phone-to-computer Agent workflows;
- existing Obsidian users who want video learning to become part of their knowledge base.

It is a weaker fit for:

- videos without usable Chinese subtitles;
- tutorials where almost all critical information exists only on screen;
- media-download or media-archival workflows;
- workflows that expect the LLM to invent missing tutorial details beyond the source.

---

## Core capabilities

- Accepts BV IDs, normal Bilibili URLs, copied text containing a BV ID, and supported `b23.tv` short links.
- Uses `yt-dlp --skip-download` by default.
- Preserves uploader descriptions, resource links, and explicit resource-access conditions.
- Does not invent templates, workflows, parameters, or resources that are missing from the source.
- Prepares long transcripts automatically and merges tiny trailing chunks.
- Allows the same BVID to be converted again; filenames use `（2）`, `（3）`, etc. instead of overwriting existing notes.
- Provides a default `light` writing flow and an optional auditable `strict` flow.
- Publishes only after the finalizer validates the draft, then removes runtime job data.
- Hermes, WorkBuddy, and Codex share one core implementation and one content standard.
- Cookie files, private notes, and machine-local configuration are ignored by Git by default.

---

## Quick start

### 1. Requirements

A normal Windows setup needs:

| Requirement | Purpose |
| --- | --- |
| Python 3.10+ | Runs the core scripts |
| yt-dlp | Collects subtitles, descriptions, and metadata |
| Bilibili Cookie file | Usually needed for authenticated subtitle/metadata access |
| Obsidian Vault | Stores the generated notes |
| Hermes / WorkBuddy / Codex | Reads the transcript and writes the learning content |

The repository does **not** bundle or auto-install `yt-dlp.exe`.

```powershell
winget install yt-dlp
```

### 2. Clone the repository

```powershell
git clone https://github.com/ZiYao00/bili-learning-automation.git
cd bili-learning-automation
```

### 3. Create machine-local configuration

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

### 4. Run doctor

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

Doctor checks Python, yt-dlp, Cookie-file presence, the Vault, CSS, taxonomy, and write permissions. It **does not read Cookie contents and does not access Bilibili**.

### 5. Install Obsidian styling

Follow [Obsidian Styling](docs/OBSIDIAN-STYLING.md) and install:

```text
learning-lab.css
video-note.css
```

into:

```text
.obsidian/snippets/
```

Then enable both snippets in Obsidian.

### 6. Choose an Agent entry point

| Agent | Typical use | Documentation |
| --- | --- | --- |
| Hermes | Send links from a phone/private chat and process them on a computer | [Installation](docs/HERMES-SKILL-INSTALL.md) |
| WorkBuddy | Convert links inside a WorkBuddy session | [Installation](docs/WORKBUDDY-SKILL-INSTALL.md) |
| Codex | Development, testing, and direct project work | Read `AGENTS.md` first |

### 7. Send a link

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

or:

```text
BVxxxxxxxxxx
```

The normal path does not require manually selecting subtitles, filenames, or note destinations.

See the full **[Quick Start](docs/QUICKSTART.md)** for detailed setup.

---

## Agents and models

The project is **not tied to a specific LLM**. Agents are thin adapters; collector, transcript preparation, taxonomy, content rules, validation, and finalization live in the shared core.

Final note quality still depends on capabilities such as:

- long-context understanding;
- factual fidelity for parameters and proper nouns;
- reconstructing relationships between multiple options;
- preserving experimental evidence;
- writing and information organization.

The project has been tested across multiple Agent/LLM environments, including same-video A/B runs. The README intentionally does not maintain a permanent model ranking because model versions, proxy backends, pricing, and capabilities change. For benchmarks, use fixed BVIDs and the same project/Skill version.

---

## Writing modes

### `light` - default

```text
read the full transcript
→ source-sufficiency check
→ write the note directly
→ separate layout pass
→ re-check transcript coverage
→ finalizer
```

Best for normal daily use.

### `strict` - optional

Adds:

```text
Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Plan
→ Source Recheck
```

Useful for auditing intermediate stages, debugging knowledge loss, or running quality regressions.

Most users should keep the default `light` mode.

---

## Privacy and local data

The following are ignored by Git by default:

```text
key/                 # Cookie / local credentials
config/local.json    # machine-specific paths
notes/**             # private learning notes
.runtime/            # temporary jobs
.codex-backups/      # local backups
archive/ materials/  # local materials
```

The public repository should only contain generic examples such as `config/local.json.example`.

> Cookie files are credentials. Do not paste Cookie contents into README files, issues, pull requests, logs, or Agent conversations.

See [SECURITY.md](SECURITY.md).

---

## Common statuses

| Status | Meaning |
| --- | --- |
| `configuration_required` | No real Obsidian Vault is bound, so collection does not start |
| `materials_ready` | Subtitles, description, and metadata are ready |
| `in_progress` | Another active job is processing the same BVID |
| `subtitle_unavailable` | No usable Chinese subtitle was obtained |
| `source_insufficient` | The current source is not sufficient for a reliable note |
| `note_ready` | Finalizer validation passed and the note was published |
| `note_invalid` | The draft failed final validation |
| `failed` | Configuration, collection, or runtime processing failed |

`in_progress` is only concurrency protection. The same BVID can be converted again after the active job ends.

---

## Documentation

| Document | Purpose |
| --- | --- |
| [Quick Start](docs/QUICKSTART.md) | Complete the first conversion from scratch |
| [Configuration](docs/CONFIGURATION.md) | Vault, Cookie, yt-dlp, and environment variables |
| [Hermes Skill Installation](docs/HERMES-SKILL-INSTALL.md) | Hermes integration |
| [WorkBuddy Skill Installation](docs/WORKBUDDY-SKILL-INSTALL.md) | WorkBuddy integration |
| [Obsidian Styling](docs/OBSIDIAN-STYLING.md) | CSS installation and troubleshooting |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common failure states |
| [Agent Integration Protocol](docs/AGENT-INTEGRATION.md) | New Agent/adaptor development |
| [Architecture](docs/ARCHITECTURE.md) | collector → transcript → Agent → finalizer |
| [Development](docs/DEVELOPMENT.md) | Tests, quality regressions, and maintenance |
| [Release Checklist](docs/RELEASE-CHECKLIST.md) | Public release checks |

---

## Development and tests

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

Public tests do not require a real Cookie and should not access a real Bilibili account.

---

## Legacy

The older Chrome/CDP + `bili-note` + `web-access` workflow is retained as historical compatibility material but is **not the default path**.

New integrations should use the yt-dlp subtitle-first pipeline. See [Legacy](docs/LEGACY.md).

---

## License

This project uses [PolyForm Noncommercial 1.0.0](LICENSE).

Personal learning, research, testing, and other non-commercial use are allowed. Commercial use is outside the scope of the current license. Third-party dependencies remain subject to their own licenses.
