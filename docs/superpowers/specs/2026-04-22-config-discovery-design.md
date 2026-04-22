# Config Discovery Design

**Date:** 2026-04-22
**Status:** Approved
**Scope:** Replace hardcoded `configFiles[]` paths in `settings.json` with a dynamic discovery system that resolves the latest backup file per device at load time.

---

## Problem

`settings.json` currently requires hardcoded absolute paths for every device config file:

```json
{ "configFiles": [{ "path": "/path/to/FW01.txt", "type": "auto" }] }
```

Oxidized writes daily backups to `/home/oxidized/backups/{SITE}_{YYYYMMDD}/` with filenames like `FRI-FW01_20260422-0500.txt`. Maintaining exact paths by hand is error-prone and breaks silently when a new day's folder appears.

---

## Solution

Add `lib/discovery.js` — a pure file-system module that resolves the correct backup path for each device at load time. `server.js` calls it once at the start of `loadAllConfigs()` and iterates the result through the existing loop unchanged.

---

## Settings Format

Replace `configFiles[]` with `backupRoot` + `devices[]`:

```json
{
  "port": 3001,
  "backupRoot": "/home/oxidized/backups",
  "devices": [
    { "name": "FRI-LTM01",  "type": "f5" },
    { "name": "GICT-LTM01", "type": "f5" },
    { "name": "SAT-FW01",   "type": "fortigate" },
    { "name": "GICT-FW01",  "type": "fortigate" }
  ],
  "fqdnFile": "/path/to/all_fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

**Field rules:**
- `backupRoot` — absolute path to the Oxidized backup root directory
- `devices[].name` — device identifier; doubles as the filename prefix (e.g. `FRI-LTM01` matches `FRI-LTM01_*.txt`)
- `devices[].type` — parser type passed through unchanged (`"f5"`, `"fortigate"`, `"paloalto"`, `"srx"`, `"auto"`)
- `configFiles` — **removed**; no longer used

---

## New Module: `lib/discovery.js`

### Exported function

```js
resolveDevicePaths(devices, backupRoot)
// returns: [{ path: string, type: string }]
```

### Algorithm (per device)

1. **Derive site prefix** — `device.name.split('-')[0]`
   - `"FRI-LTM01"` → `"FRI"`, `"GICT-FW01"` → `"GICT"`, `"SAT-FW01"` → `"SAT"`

2. **List candidate folders** — `fs.readdirSync(backupRoot)` filtered by:
   - Matches `/^{site}_\d{8}$/` exactly
   - Does **not** contain `"UCS"` (case-sensitive)
   - Sorted descending (newest date first)

3. **Search folders newest → oldest** — for each folder:
   - List all files; exclude any filename containing `"UCS"`
   - Match files whose names start with `{device.name}_` and end with `.txt`
   - Parse the timestamp suffix: extract the `HHMM` portion from `_{YYYYMMDD}-{HHMM}.txt`
   - Convert to integer for comparison (`"1700"` → `1700`, `"0500"` → `500`)
   - Pick the file with the **highest parsed timestamp** (deterministic; 1700 beats 0500)
   - If a match is found: record `{ path: absolute path, type: device.type }` and stop searching older folders

4. **If no match found across all folders** — log:
   ```
   [discovery] No backup found for {device.name} in any {site}_* folder — skipping
   ```
   and omit the device from the result.

5. **If no site folders exist at all** — log:
   ```
   [discovery] No folders found for site {site} — skipping {device.name}
   ```

### Return value

Same shape as the old `configFiles[]` entries, consumed without modification by the existing `loadAllConfigs()` loop:

```js
[
  { path: "/home/oxidized/backups/FRI_20260422/FRI-LTM01_20260422-0500.txt", type: "f5" },
  { path: "/home/oxidized/backups/GICT_20260422/GICT-LTM01_20260422-0500.txt", type: "f5" },
  { path: "/home/oxidized/backups/SAT_20260422/SAT-FW01_20260422-0500.txt", type: "fortigate" }
]
```

---

## Changes to `server.js`

Two lines change inside `loadAllConfigs()`:

**Before:**
```js
for (const entry of settings.configFiles) {
```

**After:**
```js
const resolvedFiles = resolveDevicePaths(settings.devices || [], settings.backupRoot);
for (const entry of resolvedFiles) {
```

Plus one import at the top:
```js
const { resolveDevicePaths } = require('./lib/discovery');
```

Everything else in `loadAllConfigs()` — file reading, parsing, hostname fallback, cache write — is untouched.

---

## Changes to `settings.example.json`

Replace `configFiles[]` with `backupRoot` + `devices[]` to reflect the new shape.

---

## Files Changed

| File | Change |
|---|---|
| `lib/discovery.js` | **New** — ~50 lines |
| `server.js` | +1 import, +1 line in `loadAllConfigs()`, -0 lines elsewhere |
| `config/settings.example.json` | Updated to new shape |
| `config/settings.json` | Updated to new shape (gitignored) |

---

## Error Handling

- Discovery never throws; all errors are warnings that skip the device
- Warnings are prefixed `[discovery]` for easy log grep
- A device with no resolved path is omitted from the load — existing devices are unaffected
- If `settings.devices` is missing or empty, `resolveDevicePaths` returns `[]` and `loadAllConfigs` logs zero devices loaded

---

## Out of Scope

- No changes to parser logic (`lib/parser.js`)
- No changes to `lib/scheduler.js`
- No changes to the frontend (`public/index.html`)
- No new API routes
- No caching of discovery results (runs fresh on every `loadAllConfigs()` call, which is correct — picks up new daily folders automatically)
