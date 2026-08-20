---
name: bilibili-learning
description: Turn a Bilibili plain link or BV id received in an owner private WeChat conversation into a subtitle-first Obsidian learning note without downloading media. No command prefix is required.
---

# Bilibili Learning

Treat a **plain Bilibili link** or BV id in an owner private conversation as a request to create one learning note. WeChat share cards are not supported as an input channel; if the message has no usable BV id, ask the owner to use Bilibili's “复制链接” and send that text.

## Hard boundaries

- Run only in the owner's private conversation. In groups or uncertain sender scope, ask for confirmation.
- Never read, print, upload, edit, or commit Cookie values. The collector may only pass the configured local Cookie file to yt-dlp.
- Default flow never downloads video or audio, never starts Chrome/CDP, and never falls back to ASR/transcription.
- Subtitle selection must include `ai-zh` and `zh.*`.
- Do not overwrite an existing note. A source-URL duplicate check happens before any network request.
- Raw subtitles, metadata, descriptions, and logs are temporary job data only. Do not copy them to `materials`; finalization must remove the exact job directory even when the note is invalid. A 20-minute failsafe cleanup runs if the agent crashes before finalization.

## Mandatory workflow

1. Run the collector with the received message verbatim:

   ```powershell
   $project = 'G:\GitHub\bili-learning-automation'
   python "$project\hermes-skills\bilibili-learning\scripts\prepare_ytdlp_bilibili_note.py" '<received message text>'
   ```

2. Read the JSON status.

   - `already_exists`: reply with the existing filename; do not continue.
   - `subtitle_unavailable`: reply that no usable `ai-zh`/`zh` subtitle was obtained and no media was downloaded; do not generate a note.
   - `failed`: reply with the short message; do not claim completion.
   - Only `materials_ready` may continue.

3. For `materials_ready`, read `handoff_path`, then read both project standards:

   ```text
   G:\GitHub\bili-learning-automation\docs\standards\CODEX-VIDEO-NOTE-GUIDE.md
   G:\GitHub\bili-learning-automation\docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md
   G:\GitHub\bili-learning-automation\config\bilibili-note-taxonomy.json
   ```

4. Read `job.json` and `subtitle_path`, then write the note at `note_path`. Use `canonical_title`, `category_path`, and `required_tags` exactly as returned; do not choose a new folder or title.

   - Frontmatter has exactly `author`, `published`, `duration`, `source`, `tags`.
   - Put the complete UP original description directly below the title and before the official iframe; preserve description URLs as clickable Markdown.
   - Write a short `先看结论`, `## 怎么做`, `## 容易踩坑`, and a concise practice checklist.
   - Only write claims supported by the subtitle or original description. Do not expose temporary paths, evidence IDs, or collection details in the note.
   - A genuinely empty upstream description may say `> 本视频未提供简介。`; a capture failure is not an empty description and must stop the task.
   - User-supplied resource links are not UP original description. Label them as `用户补充` if explicitly requested.

5. **Always finalize immediately after writing or on any writing failure.** This validates the note and deletes the exact temporary job directory:

   ```powershell
   python "$project\hermes-skills\bilibili-learning\scripts\finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<note_path>'
   ```

6. Reply only after finalization.

   - `note_ready`: `已完成：《标题》\n笔记：<文件名>\n已写入 Obsidian。`
   - `note_invalid` / `failed`: state the short error. Never say completed.

## Maintenance document

The owner-facing operational guide, when it exists on this Windows machine, is:

```text
G:\ai_data\hermes\docs\bilibili-learning\HERMES-BILIBILI-LEARNING-RUNBOOK.md
```

It is optional local operational documentation and must not replace the project standards above.
