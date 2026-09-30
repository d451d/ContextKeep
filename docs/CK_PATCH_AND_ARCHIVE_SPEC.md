# CK_PATCH_AND_ARCHIVE_SPEC.md — ContextKeep partial edits + memory archive
Rev 1 · 2026-09-30

## Why
`store_memory` replaces a whole record. Small updates to large memories (Spec ~51K chars,
Server ~28K, OpenLoops ~28K) cost a full rewrite each time — slow and expensive. Two fixes:
- Part B: two new MCP tools, `patch_memory` and `append_memory`, that change part of a record.
- Part D: a one-off local script that moves finished history out of three working memories
  into archive keys, verbatim, without any model rewriting the text.

Background (ContextKeep CK): V2.1 "Atlas", SQLite at `F:\ContextKeep\data\contextkeep.db`
on Gojira2022 (10.0.2.12), MCP endpoint http://10.0.2.12:5100/mcp, WebUI :5000.
Fork: github.com/d451d/ContextKeep (upstream mordang7/ContextKeep; html.unescape patch = PR #6).
Gojira2022 access from SerenityMKII: `\\10.0.2.12\c$`, `\\10.0.2.12\raid` (= F:\),
`ssh -i C:\Users\Twitch\.ssh\contextkeep_key GojiraADM@10.0.2.12`.

## Rules
- Do NOT read or write memories through the ContextKeep MCP tools, except the single test
  memory named in Part C. Part D works through a local script only.
- Do NOT change any existing tool's behaviour, the schema, categories, or any memory other
  than the four named in Part D.
- Do NOT restart any service until the step that says so.
- Stop at every STOP and report.

---

## Part A — Locate and confirm (read only, change nothing)
1. Find the running CK V2.1 server code on Gojira2022: install folder, NSSM service name(s)
   (expected something like `ContextKeep2-Server`; confirm with `nssm status` / service list),
   Python/venv used, entry file.
2. Is that folder a git repo? Remote, branch, clean or dirty (`git status`)?
   Is there also a clone on SerenityMKII (e.g. under C:\Dev\)? Which one is the source of truth
   for what is deployed?
3. Show how `store_memory` writes a record: the function(s), how `updated_at`, the edit-history
   entry and categories are written, and whether it runs in one transaction.
4. Show how tools are registered (so a new tool follows the same pattern).
5. Current row counts: memories, edit-history rows. DB file size.
6. Is there a DB backup mechanism already (e.g. F:\OneDrive\users\twitch\ContextKeep\backups\)?

STOP AFTER PART A. Report all six.

---

## Part B — Add two tools (after Twitch approves Part A)
Commit the live server code first if it is not already committed (baseline commit), then:

**`patch_memory(key, old_str, new_str)`**
- Fetch the record by exact key; error if missing.
- `old_str` must occur exactly once in the content. If 0 or 2+ matches: change nothing, return an
  error that says which, plus the match count.
- Replace it with `new_str` (empty `new_str` = delete the text).
- Keep title and categories exactly as they are.
- Write through the same code path `store_memory` uses, so `updated_at` and the edit-history
  entry are recorded the same way (history action `patched`, or whatever label the existing
  history field allows — report which).
- Return: key, new content length in characters, updated_at. Do NOT return the content.

**`append_memory(key, text)`**
- Fetch by exact key; error if missing.
- Content becomes existing content + "\n" + text. Title and categories unchanged.
- Same write path, history action `appended`. Same short return as above.

Both: one transaction per call; `html.unescape` handling unchanged; no other tool touched.

Checks: the server parses/imports cleanly (no service restart yet). Show the diff.

STOP AFTER PART B. Do not commit or deploy until Twitch says so.

---

## Part C — Deploy and test (after Twitch approves Part B)
1. Commit (`CK: add patch_memory and append_memory`). Push to the fork if that is the
   existing practice (report either way).
2. Back up the DB with the SQLite backup API (safe while the server runs), e.g.
   `python -c "import sqlite3; s=sqlite3.connect(r'F:\ContextKeep\data\contextkeep.db'); d=sqlite3.connect(r'F:\ContextKeep\data\contextkeep-pre-patch-20260930.db'); s.backup(d); d.close(); s.close()"`
   Report the backup's size and its memory count.
3. Restart the CK MCP service only (service name from Part A). Confirm it is running.
4. Test with a throwaway memory `Twitch_Test_PatchTool` (categories `Uncategorized`):
   store "line one\nline two\nline three"; patch "line two" → "LINE TWO"; patch "line" (must
   fail: 2 matches); patch "absent" (must fail: 0 matches); append "line four";
   retrieve and show the content; show its edit history; then delete it.
5. Confirm title and categories were unchanged after the patch and append.

STOP AFTER PART C. Report.

---

## Part D — One-off archive + de-duplication (after Twitch approves Part C)
A local Python script run on Gojira2022 against the DB through CK's own storage functions
(same write path as the tools, so history is recorded). No model rewrites any text: sections
move VERBATIM.

**Dry run first:** the script writes the proposed new contents of all four records to
`C:\Dev\Claude\ck-archive-dryrun\` (one .md per key) and changes nothing in the DB.

### D1. `Twitch_OpenLoops` → new `Twitch_OpenLoops_Closed`
- Move every section from the first line starting `## Closed ` to the end of the content.
- In `Twitch_OpenLoops`, put in their place one line:
  `Closed items are archived in \`Twitch_OpenLoops_Closed\` (newest first; add new closures there with append_memory or patch_memory).`
- New key `Twitch_OpenLoops_Closed`, title `Open Loops — Closed Items (archive)`, categories
  `Projects, Workflows & Automation`, content = `# Open Loops — Closed Items (archive)` +
  blank line + `Moved from Twitch_OpenLoops on 2026-09-30. Verbatim.` + blank line + the moved sections.

### D2. `Twitch_PluginStation_Spec` → new `Twitch_PluginStation_History`
A section = its heading line up to (not including) the next line starting with `#### `, `### `,
`## ` or `---`.
Move these sections (match the heading line by its start):
- `#### VST3 bundle metadata fix (Part C) ✅`
- `#### Part B UI fixes ✅`
- `#### BUG 7 fix — usage matcher per-format tiers ✅`
Replace each with one line: `<heading line> — full write-up moved to Twitch_PluginStation_History.`
Also move:
- The whole `## Plugin Counts (SerenityMKII)` section body (keep the heading). Replace the body
  with: `- Counts (current and past): Twitch_PluginStation_Server → Plugin Counts. Standing rule: delete AAX on sight.`
- The two bullets starting `- Deployed Scan-Plugins.ps1 (` and `- Deployed Scan-PluginUsage.py (`.
  Replace both with one bullet:
  `- Deployed versions + SHA256s: Twitch_PluginStation_Server → Service → Latest deployed commits.`

### D3. `Twitch_PluginStation_Server` → same `Twitch_PluginStation_History`
- Move every section whose heading starts `#### BUG ` (same section rule as D2).
- Replace them, in the same place, with an index: one line per moved section,
  `- <heading text without "#### "> — write-up in Twitch_PluginStation_History.`
- Leave `#### UI complaint, not a bug …` and everything else in place.

### `Twitch_PluginStation_History` (new)
Title `PluginStation — History (archive)`, categories `Projects, Knowledge & Research`.
Content: `# PluginStation — History (archive)`, blank line,
`Moved verbatim on 2026-09-30 from Twitch_PluginStation_Spec and Twitch_PluginStation_Server.`,
then `## From Twitch_PluginStation_Spec` + the D2 moved text in original order, then
`## From Twitch_PluginStation_Server — bug write-ups` + the D3 moved text in original order.

### Dry-run checks (report all)
1. Before/after character counts for all four keys.
2. No text lost: for each source memory, every line of the original appears in the new source
   content or in its archive, in the same order within each moved section. Only the named
   pointer/index lines are new. Report any line that fails.
3. Categories and titles of the existing keys unchanged.
4. Any heading from D1–D3 that was NOT found → report it and do not guess.

STOP AFTER THE DRY RUN. Twitch approves, then:

### Apply
1. New DB backup (same method, name `…-pre-archive-20260930.db`).
2. Run the script for real. Create the two new keys first, then patch the three sources.
3. Retrieve each of the four keys through the normal CK read path and confirm the content
   equals the dry-run files byte for byte. Report sizes and edit-history entries.

STOP. Report.

---

## Rev 2 — decisions after Part A
1. Leave docs/DIRECTIVE_UPDATE.md exactly as it is (not committed, not restored). Do not commit the .bak file. Commit scripts/backup_db.py on its own: "Track backup_db.py (used by the ContextKeep DB Backup task)".
2. Copy the spec into the repo as docs/CK_PATCH_AND_ARCHIVE_SPEC.md and commit it on its own, before any code change.
3. get_contextkeep_info: add patch_memory and append_memory to its tool list. That is the only change allowed to an existing tool.
4. Key lookup is case-insensitive (COLLATE NOCASE), same as every other tool.
5. patch_memory and append_memory: do the read and the write inside one BEGIN IMMEDIATE transaction. Pass the record's existing categories back so nothing falls back to Uncategorized.
6. Do not push anything to any remote during this work. Local commits only.
7. Codex review bundle (Codex cannot reach Gojira): at the Part B stop, write the full diff to C:\Dev\Claude\ck-codex\part-b.diff plus copies of the changed server.py and core\memory_manager.py. At the Part D dry-run stop, add the script and the four dry-run files to the same folder.
8. patch_memory and append_memory must not touch categories at all. Add an optional preserve_categories: bool = False to store_memory. When True (update only): skip the Uncategorized fallback, do not delete or re-insert memory_categories rows, do not recalculate category counts, and do not log categories_changed. Only content, updated_at, lines, chars and the single patched/appended history entry are written. _edit_content passes preserve_categories=True and no longer builds a category list. With the flag left out, store_memory behaves exactly as before.
