# Portability, updates and backups

## Move or back up

Run `bash launch.sh --stop`, then copy the whole folder to another directory/computer. It may contain spaces. Run its launch.sh again; no original installation or project filesystem is needed. Existing entries/source text remain readable if external files are missing (−).

Application code is in app/; user entries, imports, archives, preferences and backups are in data/. Back up data/ separately whenever desired. Do not omit entries, source evidence, project catalog, overviews or archives. The search.sqlite index is disposable; the runtime/lock/log files are not historical authority. Backups are not encrypted automatically.

For a new clean application version, stop the old server, copy your data/ into the new folder without replacing it with empty defaults, then launch. Updating app/, launch.sh and documentation must not replace data/. Back up first; do not run two versions against the same data at once.

## Search index

Click Rebuild search or run `bash launch.sh --rebuild-index`. A running instance receives the request through its local API; otherwise offline maintenance takes the writer lock. A missing index rebuilds on startup. Markdown body versions plus JSON metadata are authoritative.

## Archive/reopen a project

Review and approve its entries, select it and open Project overview / Keep files. Save overview edits; inspect the approved-entry preview and selected files; explicitly archive. Only approved, non-excluded records/source evidence enter the portable archive. External files, even Keep selections, are not automatically copied.

The active journal retains frozen archived records in global search, while new work receives a new period. Project Archives opens the snapshot on its overview, with read-only history/search. Excluded/unapproved material remains outside the snapshot.

Each data/archives/archive-… folder includes its own runtime, overview, record bodies and source evidence. Copy that folder elsewhere and run its launch.sh independently. To restore your active journal, restore the entire backed-up data/ folder; read-only snapshots cannot silently be edited or thawed. To continue a project, use the active journal's new period. External snapshot import into another active catalog is not implemented.

## Stop/reopen and troubleshooting

`bash launch.sh --stop` verifies the current folder's instance before asking it to stop. It does not kill an unrelated PID. Repeated launch reopens an existing responsive instance. Stale runtime information is ignored; a writer lock prevents duplicate servers. A paused/unresponsive instance holding that lock gives a clear error; resume/stop it from its own terminal rather than deleting its lock or killing an arbitrary process.

Ports are chosen locally; an occupied preferred port is not reclaimed from another application. The launcher prints the actual URL and opens your default browser. Use `bash launch.sh --no-browser --port 0` for headless operation. If a browser cannot be opened, copy the printed URL into one manually. Runtime errors are in data/server.log, not included in a clean/public package.

The portable .desktop launcher uses its own location, not a fixed home path. File managers differ in trust policy; mark it trusted/allow launching or use the terminal fallback. Python3.10+, SQLite FTS5 and system tzdata are needed; install missing OS packages yourself through your distribution's software manager. No automatic installation occurs.
