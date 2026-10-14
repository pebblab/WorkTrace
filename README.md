# Living Journal

### Searchable AI conversation history, project decisions, and work records — on your own computer.

**Living Journal** is a small, offline-first Linux application for keeping track of work done with ChatGPT, Pi, coding agents, and other AI tools. It brings conversation-based records, projects, decisions, and file references into one searchable place — without requiring an AI service to read or maintain your journal.

It's **not another diary app or an Obsidian replacement**. Its purpose is to keep the *history behind the work*: what was requested, what was suggested or done, which files were involved, and where a project was left.

> **Version 1.0.0:** Portable Linux application, tested on Linux Mint. The GitHub repository is **WorkTrace**; the application and portable folder remain **Living Journal / LivingJournal**. [Download the portable release](https://github.com/pebblab/WorkTrace/releases/tag/v1.0.0). No Git, Pi, or AI subscription is required to use it.

## Why I built it

I work on several projects with AI assistants. At first, each project lived in its own folder, and I had a pretty good idea of what was in it. I knew where the code was, which files mattered, and what had changed.

Then the projects began to overlap.

One conversation could start with a website feature and end with a product idea. A technical problem could lead to a design decision for another application. Some projects became parts of larger projects; others went on hold and might be reopened later. Chat titles and folder names stopped being reliable descriptions of the work inside them.

Meanwhile, every AI-assisted session produced more material: scripts, datasets, reports, screenshots, documentation, revisions, and temporary files. Some outputs were essential. Others were just steps along the way. Files were copied, renamed, superseded, or deleted. A conversation might mention an output without proving that it was ever saved.

Eventually, I had a large collection of chats and thousands of files. The problem wasn't that I had forgotten the work. **The record existed, but it was scattered between conversations and folders.** To find why something changed, I had to reconstruct the story all over again.

I wanted a professional work history, but not a system that needed constant administration. I didn't want to fill in a dozen fields every evening, depend on one AI provider's memory, or preserve every temporary screenshot forever.

I wanted to be able to ask:

- What was I trying to do on a particular day?
- Which requests and responses led to this implementation?
- Was something completed, or merely proposed?
- Where are the input files and generated outputs?
- Why did the direction of a project change?
- Which projects touched the same ideas or files?
- What should I know before reopening a project months later?

Living Journal grew out of that need.

## Why conversation exchanges, not automatic AI summaries?

My first attempt was ambitious: reconstruct the entire history from AI-generated summaries of old chats. The extraction preserved useful evidence, but the summaries also sometimes merged unrelated activities, mistook suggestions for decisions, and made ordinary one-off requests look like significant project milestones.

I chose a simpler unit: **one user prompt and its associated assistant responses form one historical entry**.

The exchange keeps its context. I can give it a meaningful headline, associate it with a project, search it, edit its presentation, or exclude it from my working journal. The underlying conversation remains the reference. Detailed agent reports can be linked when a session needs more technical depth.

A request for ten example sentences doesn't have to become a major development event. But if that conversation contains the explanation for an important decision, I can still find it.

The goal is not for AI to decide which parts of my history deserve to survive. The goal is to make that history easy enough **for me to decide**.

## What it does

### Find the conversation behind a change

Search your journal across entry text, headlines, projects, and file references. Results show relevant snippets and highlight matches. Use ordinary text for partial matching, or double quotes for whole words and phrases:

| Search | Meaning |
|---|---|
| `cat` | Find occurrences including `category` or `catch` |
| `"cat"` | Find the standalone word *cat* |
| `"stress pattern"` | Find that exact phrase |

Filter by project or date to narrow your results.

### Keep a simple, readable work journal

Create an entry with a project and a note — no elaborate form. Historical exchanges can be reviewed, retitled, edited, kept, or excluded from normal views without destroying their source record.

### Follow work across projects

Browse a universal chronology or focus on one project. Projects do not have to be isolated: conversations can cross boundaries, and an idea can reappear in a different part of your work. Keep project overviews for context.

### Remember files without hoarding everything

Living Journal distinguishes files **provided as inputs**, **reported generated outputs**, and ordinary references. A stored local file association can display `✓` when the file is available; unresolved or unavailable references show `−`. Conversation import creates documentary references, not automatically verified matches on disk.

File records can be marked **Keep**, **Reference**, or **Ignore**. Keep marks future preservation; it does **not** automatically copy external files. A missing temporary file doesn't make its conversation disappear, and a file mention is not proof that the file exists or that an assistant created it.

### Pause and reopen projects

Archive a project overview and its approved, non-excluded entries with their source evidence in a self-contained read-only snapshot. Later, open that archive independently while continuing the active project in a new work period. External project files are not automatically included.

### Accept optional AI-agent drafts

An agent can prepare a journal entry or work-session report using the documented draft format. Review and approve it before adding it to the official journal. AI is optional; ordinary reading, writing, and searching work without it.

### Keep it local and portable

Living Journal runs on `localhost` in your browser. The portable release is intended for Linux Mint and comparable Linux systems. It does not require an AI subscription, cloud account, or public server. Journal data is kept separate from the application so it can be backed up and moved.

## A typical workflow

**During a project:** Work normally in your editor or AI assistant.

**After a session:** Write a short entry, or review a draft prepared by an agent. Record the result and any relevant files. Keep it brief unless the technical details matter.

**Later:** Search for a term, inspect the original exchange, follow file references, or read the project overview.

**When a project pauses:** Archive its work period. When you return, open that history and start a new period.

## Getting started on Linux

1. Download `LivingJournal-1.0.0.tar.gz` from the repository's [Releases page](https://github.com/pebblab/WorkTrace/releases).
2. Extract the `LivingJournal` folder anywhere you have permission to write.
3. Open that folder and run:

   ```bash
   bash launch.sh
   ```

4. The launcher checks the local runtime requirements, starts the local server, and opens Living Journal in your browser.

The launcher uses an available localhost port, reopens the same running instance on repeated launch, and leaves unrelated servers alone. Closing the browser does not stop the server; run `bash launch.sh --stop` to stop this copy safely. You can also double-click `LivingJournal.desktop` and allow launching if your file manager asks; terminal launch is the reliable fallback.

Requirements: Python 3.10+, standard-library SQLite with FTS5, system timezone data, and a browser. No pip packages or frontend build are needed. The launcher checks dependencies but never installs them automatically. You do not need a `.deb` package or administrator privileges.

See [`docs/QUICK_START.md`](docs/QUICK_START.md) for first-use instructions and [`docs/PORTABILITY.md`](docs/PORTABILITY.md) for moving or backing up your journal.

## Bringing in AI conversations: what is supported?

There are **three different workflows**, and they should not be confused:

| Workflow | What it means |
|---|---|
| Manual entry | Write and save notes directly in Living Journal |
| Agent draft | Use a compatible local draft format; review the draft before approval |
| Conversation-file import | Import one supported local `.md` or `.txt` transcript at a time; review the resulting exchanges |

### Supported local conversation import

Click **Import conversation**, choose a project, then select a local `.md` or `.txt` file (or paste its text). The importer recognizes explicit `User:` / `Assistant:` speaker markers, including optional heading prefixes, and the specific `# you asked` / `# chatgpt response` Markdown format. For example:

```text
User: Help me plan a garden experiment.
Assistant: Compare two watering schedules and record growth.
User: Suggest a simple record sheet.
Assistant: Use date, watering schedule, plant height, and observations.
```

This creates two separate prompt-and-response entries. Consecutive assistant responses stay with the preceding prompt. Unpaired messages are retained and flagged. Imported entries stay **unapproved until human review**.

The submitted transcript text is preserved once locally, with source-name/hash and message line/UTF-8-byte-range provenance references linked from entries. This preserves submitted text, not necessarily original file bytes or encoding; the selected file is not moved or altered. Identical submitted text is deduplicated journal-wide, even under another filename or project. Changed text may create a new import.

Recognized `message time:` timestamps are imported where available. Explicit offsets are converted to America/New_York for display; offset-free times use a clearly marked New York assumption. Missing timestamps stay unknown and may affect chronological ordering; tied or missing times do not guarantee source-sequence ordering in journal views.

Importing runs **entirely offline**, without an AI model, Pi, agent, or provider account.

### Current import limitations

- No direct connection to ChatGPT, Claude, Gemini, or other services; no login, scraping, or shared-link retrieval.
- No provider-specific JSON/ZIP export import.
- No batch-file import; import additional files sequentially.
- No reliable parsing of arbitrary unstructured transcripts or universal provider-export compatibility.
- No automatic recovery of attachments, PDFs, images, or original generated files.
- Missing/unparseable timestamps may prevent reliable chronological ordering.

JSON is supported for **preformatted journal-entry drafts**, not as a provider conversation-export format. Draft import creates one draft per object and does not split conversations pasted into its text.

The original **47-conversation historical reconstruction** used a **separate processing workflow**. That reconstruction, its semantic analysis and filesystem inventory are not portable-edition features or bundled private data.

See [`docs/IMPORT_CHATS.md`](docs/IMPORT_CHATS.md) for the exact markers, timestamp handling and provenance details.

## What Living Journal is not

- **Not a general-purpose notes vault.** It is organized around work, conversations, projects, and their provenance.
- **Not Git.** Keep source-code versions in Git; use Living Journal to understand the discussion and decisions around them.
- **Not an AI fact checker.** An assistant's claim of implementation is not automatically proof that a feature works.
- **Not a mandatory file archive.** You choose which outputs are worth preserving.
- **Not tied to any one AI provider.** Your existing records remain readable without that provider.

## Privacy and data ownership

Living Journal is local-first. The public application distribution is intended to contain **no personal journal, conversation archive, or private project files**. Your data stays with your copy of the application unless you choose to share it.

Before publishing a journal archive or attaching files to an issue, inspect them for private conversation content, file paths, and credentials.

## Documentation

- [Quick Start](docs/QUICK_START.md)
- [Conversation Imports](docs/IMPORT_CHATS.md)
- [Agent Draft Workflow](docs/AGENT_WORKFLOW.md)
- [Portability and Backups](docs/PORTABILITY.md)

## License

MIT License. Copyright (c) 2026 **Pebblab**. See [LICENSE](LICENSE).

User journal data is not licensed or distributed automatically with the application. No fonts, browsers or other third-party assets are bundled; external OS runtimes retain their own licenses. See [THIRD_PARTY.md](THIRD_PARTY.md).

## Operational limitations

This is a trusted single-user localhost tool, not a public/multi-user server. Markdown is a safe limited subset. Substring and quoted matching scan the derived SQLite fields and can slow on very large journals. Data is not automatically encrypted. Stop before moving or updating; back up `data/` first. A hard interruption during an archive's active-catalog transition may require manifest-based reconciliation. See the portability guide for recovery boundaries.

---

**AI tools help us create more work. Living Journal helps us find, understand, and carry that work forward.**
