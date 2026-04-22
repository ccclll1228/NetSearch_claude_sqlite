# Config Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded `configFiles[]` paths in `settings.json` with a dynamic discovery system that resolves the latest Oxidized backup file per device at load time.

**Architecture:** A new `lib/discovery.js` module scans `/home/oxidized/backups/{SITE}_{YYYYMMDD}/` folders, derives the site from each device name (`FRI-LTM01` → `FRI`), and returns `[{path, type}]` in the same shape `loadAllConfigs()` already consumes. `server.js` calls it at the top of `loadAllConfigs()` with two line changes and one new import. Settings switches from `configFiles[]` to `backupRoot` + `devices[]`.

**Tech Stack:** Node.js `fs`, `path` (stdlib only — no new dependencies)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `lib/discovery.js` | **Create** | Folder scan, file matching, timestamp selection |
| `server.js` | **Modify** | +1 import; replace `configFiles` iteration with `resolveDevicePaths()` result |
| `config/settings.example.json` | **Modify** | Update template to `backupRoot` + `devices[]` shape |
| `config/settings.json` | **Modify** | Replace placeholder paths with real device list |

---

## Task 1: Create `lib/discovery.js`

**Files:**
- Create: `lib/discovery.js`

- [ ] **Step 1: Write `lib/discovery.js`**

Create the file with this exact content:

```js
'use strict';
const fs   = require('fs');
const path = require('path');

function resolveDevicePaths(devices, backupRoot) {
  const resolved = [];

  for (const device of devices) {
    const site = device.name.split('-')[0];

    // Collect site folders, exclude UCS (safety belt — site regex already prevents it)
    let folders;
    try {
      folders = fs.readdirSync(backupRoot)
        .filter(f => new RegExp(`^${site}_\\d{8}$`).test(f) && !f.includes('UCS'))
        .sort()
        .reverse(); // newest date first
    } catch (err) {
      console.warn(`[discovery] Cannot read backupRoot ${backupRoot}: ${err.message}`);
      continue;
    }

    if (folders.length === 0) {
      console.warn(`[discovery] No folders found for site ${site} — skipping ${device.name}`);
      continue;
    }

    let found = false;
    for (const folder of folders) {
      const folderPath = path.join(backupRoot, folder);
      let files;
      try {
        files = fs.readdirSync(folderPath);
      } catch (err) {
        console.warn(`[discovery] Cannot read ${folderPath}: ${err.message}`);
        continue;
      }

      // Match device files, exclude UCS
      const candidates = files.filter(f =>
        f.startsWith(device.name + '_') &&
        f.endsWith('.txt') &&
        !f.includes('UCS')
      );

      if (candidates.length === 0) continue;

      // Parse HHMM timestamp from filename: DEVICE_YYYYMMDD-HHMM.txt
      const scored = candidates.map(f => {
        const m = f.match(/_\d{8}-(\d{4})\.txt$/);
        return { f, ts: m ? parseInt(m[1], 10) : -1 };
      });

      // Highest timestamp wins; ties broken by lexicographic order (last wins)
      scored.sort((a, b) => b.ts !== a.ts ? b.ts - a.ts : (b.f > a.f ? 1 : -1));

      const winner = scored[0];
      const absPath = path.join(backupRoot, folder, winner.f);
      resolved.push({ path: absPath, type: device.type });
      console.log(`[discovery] ${device.name} → ${folder}/${winner.f}`);
      found = true;
      break;
    }

    if (!found) {
      console.warn(`[discovery] No backup found for ${device.name} in any ${site}_* folder — skipping`);
    }
  }

  return resolved;
}

module.exports = { resolveDevicePaths };
```

- [ ] **Step 2: Verify discovery resolves real devices**

Run this inline test against the real backup root:

```bash
node -e "
const { resolveDevicePaths } = require('./lib/discovery');
const devices = [
  { name: 'FRI-LTM01',  type: 'f5' },
  { name: 'SAT-FW01',   type: 'fortigate' },
  { name: 'GICT-LTM01', type: 'f5' },
  { name: 'FAKE-XX99',  type: 'auto' },
];
const result = resolveDevicePaths(devices, '/home/oxidized/backups');
console.log('Resolved:', JSON.stringify(result, null, 2));
console.log('Count:', result.length, '(expect 3 — FAKE-XX99 skipped with warning)');
"
```

Expected output:
```
[discovery] FRI-LTM01 → FRI_20260422/FRI-LTM01_20260422-0500.txt
[discovery] SAT-FW01 → SAT_20260422/SAT-FW01_20260422-0500.txt
[discovery] GICT-LTM01 → GICT_20260422/GICT-LTM01_20260422-0500.txt
[discovery] No folders found for site FAKE — skipping FAKE-XX99
Resolved: [
  { "path": "/home/oxidized/backups/FRI_20260422/FRI-LTM01_20260422-0500.txt", "type": "f5" },
  { "path": "/home/oxidized/backups/SAT_20260422/SAT-FW01_20260422-0500.txt", "type": "fortigate" },
  { "path": "/home/oxidized/backups/GICT_20260422/GICT-LTM01_20260422-0500.txt", "type": "f5" }
]
Count: 3 (expect 3 — FAKE-XX99 skipped with warning)
```

If count is not 3 or paths are wrong, check folder names with:
```bash
ls /home/oxidized/backups/ | grep -E '^(FRI|SAT|GICT)_' | sort -r | head -6
```

- [ ] **Step 3: Commit**

```bash
git add lib/discovery.js
git commit -m "feat: add lib/discovery.js — dynamic backup file resolution"
```

---

## Task 2: Update `server.js`

**Files:**
- Modify: `server.js` (line 6 area for import; line 63 area for loop)

- [ ] **Step 1: Add the import**

In `server.js`, after the existing `require` lines (around line 7), add:

```js
const { resolveDevicePaths } = require('./lib/discovery');
```

The require block should look like:

```js
const { parseConfig, parseFqdnFile } = require('./lib/parser');
const { startScheduler } = require('./lib/scheduler');
const { resolveDevicePaths } = require('./lib/discovery');
```

- [ ] **Step 2: Replace the configFiles loop**

In `loadAllConfigs()`, find this line (around line 63):

```js
    for (const entry of settings.configFiles) {
```

Replace it with these two lines:

```js
    const resolvedFiles = resolveDevicePaths(settings.devices || [], settings.backupRoot);
    for (const entry of resolvedFiles) {
```

Everything else in `loadAllConfigs()` stays unchanged — the loop body, `fs.existsSync`, `parseConfig`, hostname fallback, cache write — all untouched.

- [ ] **Step 3: Verify the file still parses cleanly**

```bash
node -e "require('./server.js')" 2>&1 | head -5
```

Expected: server starts (shows `[server] NetSearch running at http://localhost:3001`) with no syntax errors. Kill it with Ctrl-C after confirming startup.

- [ ] **Step 4: Commit**

```bash
git add server.js
git commit -m "feat: wire resolveDevicePaths into loadAllConfigs"
```

---

## Task 3: Update settings files

**Files:**
- Modify: `config/settings.example.json`
- Modify: `config/settings.json`

- [ ] **Step 1: Update `config/settings.example.json`**

Replace the entire file content with:

```json
{
  "port": 3000,
  "backupRoot": "/home/oxidized/backups",
  "devices": [
    { "name": "FRI-LTM01",  "type": "f5" },
    { "name": "FRI-LTM02",  "type": "f5" },
    { "name": "FRI-FW01",   "type": "fortigate" },
    { "name": "FRI-FW02",   "type": "fortigate" },
    { "name": "GICT-LTM01", "type": "f5" },
    { "name": "GICT-LTM02", "type": "f5" },
    { "name": "GICT-FW01",  "type": "fortigate" },
    { "name": "GICT-FW02",  "type": "fortigate" },
    { "name": "SAT-LTM01",  "type": "f5" },
    { "name": "SAT-LTM02",  "type": "f5" },
    { "name": "SAT-FW01",   "type": "fortigate" },
    { "name": "SAT-FW02",   "type": "fortigate" }
  ],
  "fqdnFile": "/path/to/all_fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

- [ ] **Step 2: Update `config/settings.json`**

Replace the entire file content with:

```json
{
  "port": 3001,
  "backupRoot": "/home/oxidized/backups",
  "devices": [
    { "name": "FRI-LTM01",  "type": "f5" },
    { "name": "FRI-LTM02",  "type": "f5" },
    { "name": "FRI-FW01",   "type": "fortigate" },
    { "name": "FRI-FW02",   "type": "fortigate" },
    { "name": "GICT-LTM01", "type": "f5" },
    { "name": "GICT-LTM02", "type": "f5" },
    { "name": "GICT-FW01",  "type": "fortigate" },
    { "name": "GICT-FW02",  "type": "fortigate" },
    { "name": "SAT-LTM01",  "type": "f5" },
    { "name": "SAT-LTM02",  "type": "f5" },
    { "name": "SAT-FW01",   "type": "fortigate" },
    { "name": "SAT-FW02",   "type": "fortigate" }
  ],
  "fqdnFile": "/path/to/all_fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

Note: `settings.json` is gitignored. Update the `fqdnFile` path to the real CSV location when known.

- [ ] **Step 3: Commit `settings.example.json`**

(`settings.json` is gitignored — do not commit it.)

```bash
git add config/settings.example.json
git commit -m "feat: update settings.example.json to backupRoot + devices[] shape"
```

---

## Task 4: End-to-end smoke test

**Goal:** Confirm the running server discovers and loads all 12 devices without errors.

- [ ] **Step 1: Restart the dev server**

If the server is already running, stop it (Ctrl-C in its terminal), then:

```bash
npm run dev
```

Watch for `[discovery]` lines in startup output. Expected (one per device):
```
[discovery] FRI-LTM01 → FRI_20260422/FRI-LTM01_20260422-0500.txt
[discovery] FRI-LTM02 → FRI_20260422/FRI-LTM02_20260422-0500.txt
...
[load] Done. 12 devices loaded.
```

- [ ] **Step 2: Check `/api/status`**

```bash
curl -s http://localhost:3001/api/status | node -e "
const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
console.log('lastLoaded:', d.lastLoaded);
console.log('device count:', d.devices.length, '(expect 12)');
d.devices.forEach(x => console.log(' ', x.type, x.hostname, 'rules:', x.ruleCount));
"
```

Expected: 12 devices, each with a hostname and non-zero ruleCount (F5 LTMs show pools/virtuals, FortiGate FWs show secRules).

- [ ] **Step 3: Trigger a manual reload and verify re-discovery**

```bash
curl -s -X POST http://localhost:3001/api/reload | node -e "
const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
console.log(d);
"
```

Expected: `{ ok: true, lastLoaded: '<ISO timestamp>' }`

Server log should show `[discovery]` lines again — confirming discovery re-runs on every reload and will automatically pick up new daily folders.

- [ ] **Step 4: Verify no `[discovery]` warnings for valid devices**

```bash
# grep server log output for any unexpected warnings
# If running in foreground, scroll up — no lines like:
# [discovery] No backup found for ... — skipping
# should appear for the 12 valid devices
```

If a device is missing, check:
```bash
ls /home/oxidized/backups/ | grep -E '^(FRI|GICT|SAT)_' | sort -r | head -3
ls /home/oxidized/backups/FRI_20260422/ | grep LTM
```
