# Runtime and asset inventory

Included: application-specific Python code, vanilla JavaScript Markdown renderer/highlighting, CSS/HTML, shell/desktop launchers, synthetic tests and documentation. No vendored third-party code, browser binaries, Python packages, icons, photos, fonts or datasets are included. The desktop icon is a standard theme name, not an embedded asset.

Required external runtime: Python3.10+, its standard library (including SQLite/zoneinfo), system SQLite with FTS5, and timezone data. Recommended: a local browser and desktop browser association. These are supplied/licensed by the Linux distribution, not relicensed under this application's MIT License. Optional browser testing uses an independently installed Playwright/browser through an environment variable; neither is packaged or needed to use the app.

Font family references are not font redistribution. Century Gothic and Avant Garde are used only if already legally installed; otherwise a local sans-serif fallback renders responses. No font download/external stylesheet is used.

Application copyright holder: Pebblab, designated by the owner for this MIT release. Inspection of the reused application code found no third-party copyright notices, vendored libraries or additional attribution requirements. User-created/imported data has separate rights and is never included in a clean release.
