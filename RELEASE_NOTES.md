# Living Journal v1.0.0

A portable offline-first Linux work history for manual notes and AI-assisted projects. The GitHub repository is WorkTrace; the application remains Living Journal.

## Install

Download `LivingJournal-1.0.0.tar.gz`, extract it somewhere writable, open the LivingJournal folder, and run:

```sh
bash launch.sh
```

Or double-click LivingJournal.desktop and allow launching. The launcher checks Python 3.10+, SQLite FTS5 and system tzdata, selects an available loopback port, and opens your browser. No Git, Pi, AI subscription, pip install, frontend build or administrator privileges required. Stop with `bash launch.sh --stop`.

## Included

- Preserved dark UI, prompt/response typography and comfortable cards.
- Manual entries, project/date filters, substring and quoted whole-word/phrase search with snippets/highlighting.
- One-file-at-a-time local .md/.txt import using explicit User:/Assistant: or # you asked/# chatgpt response markers; exchange grouping, source provenance, recognized timestamps and identical-text duplicate prevention.
- Human review of unapproved imported exchanges and optional preformatted JSON entry drafts.
- Arbitrary projects/categories, editable overviews, file-reference choices and self-contained approved-only read-only work-period archives.
- Empty initial data, code/data separation, relocation, safe single-instance startup and verified stop.

## Limits

No direct provider integration, provider JSON/ZIP importer, batch-file importer, reliable arbitrary-prose parsing or attachment recovery. Missing timestamps affect chronology. External project files are not copied automatically. The historical 47-conversation reconstruction is a separate workflow, not a bundled feature or dataset. Markdown is a safe subset; very large journals may search slowly. Back up data before moving/updating; archive/catalog interruption can require reconciliation.

Tested independently on Linux Mint, including the exact release archive, real local file selection, manual entries, quoted search, restart persistence and relocation. See README and docs for supported formats and operational limits.

MIT License — Copyright (c) 2026 Pebblab. No personal journal data or third-party binaries/fonts included.
