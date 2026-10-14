# Import conversations

Create/select a project, then click **Import conversation**. Choose a local .txt/.md file or paste text, select its project, and import. Nothing is fetched online.

## Supported plain transcript

```text
User: Help me plan a garden experiment.
Assistant: Compare two watering schedules and record growth.
User: Suggest a simple record sheet.
Assistant: Use date, schedule, plant height, and observations.
```

Each User: marker begins a new exchange. Consecutive Assistant: responses stay with that prompt. Markers must begin a line; content may follow the colon or begin on the next line. Optional heading prefixes (# User:) are supported. Fenced code blocks are not parsed as role markers.

## Supported structured Markdown dialect

```markdown
# you asked
message time: 2026-07-01T10:00:00-04:00
Prepare a garden record sheet.
---
# chatgpt response
Use a small table with date and observations.
```

Only this explicit # you asked / # chatgpt response dialect is supported for platform-style Markdown exports. Not every platform/exporter uses it. The optional message time: line may be an ISO date/time; its original string is retained. Explicit offsets convert to America/New_York for display. Missing times remain unknown; date-only values remain date-only. Without an offset, New York is an **assumption**, not an inferred fact about the provider—review/edit the imported date.

## Evidence and review

The original supplied text is stored once locally and linked from every exchange, with its SHA256 and message line/byte ranges. Stable IDs and a source hash prevent importing the identical transcript twice, even into another project. An interrupted retry retains already-created entries and does not overwrite their edits.

Imported entries are not automatically approved. Edit/approve them before archiving. An orphan assistant or prompt without a response is retained and flagged. The importer does not turn suggestions into completed work, merge unrelated prompts, or recover binary attachments.

Explicit user @filename references/file links appear as inputs; assistant sandbox output links appear as reported outputs. Other filename/web references are not assumed to be generated files. Associated file references start unverified (−); source transfers or original versions are not independently proved. Keep marks future preservation, Reference retains metadata, Ignore hides normal display.

Unsupported: provider JSON/ZIP exports, universal provider compatibility, PDF/image/OCR import, automatically paired arbitrary prose, shared-link retrieval, login automation or scraping. Convert unsupported material into the role-marked format yourself and retain any original timestamp uncertainty.
