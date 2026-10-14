# Optional agent drafts

Normal use never requires an agent. Any tool or person can prepare local JSON:

```json
{
  "id": "garden-note-001",
  "status": "draft",
  "project": "project-key-from-the-journal",
  "headline": "Review the watering experiment",
  "date": null,
  "text": "A proposed journal note. Distinguish reported results from verified observations.",
  "sources": [{"reference": "Local experimental notes"}],
  "files": [{"name": "observations.csv", "direction": "provided"}]
}
```

The existing project key is available in the project selector's value or local data/projects.json. Project and nonempty text are required. Headline, summary, date and documentary sources/files are optional. Files use provided/generated/reference. Absent date means unknown, not fabricated. Agent presence claims are discarded; file references begin unverified.

Paste JSON into **Review drafts**, or run `bash launch.sh --import-draft draft.json`. When already running, the launcher imports through the local API. Stable submission IDs prevent duplicates. The human can change text/headline/project/date, approve or reject. An unapproved/rejected draft is not indexed as an official entry. Retried approval does not duplicate a record.

Pi, ChatGPT or any other tool may help produce the JSON, but there is no provider integration, model-specific SDK, cloud/API dependency, login adapter or automatic daily update. Sources supplied as documentary references remain text; no external pages are fetched. Journal approval is not scientific verification of an agent's claims.
