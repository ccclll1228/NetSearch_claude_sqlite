# NetSearch Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Node.js/Express backend so config files are parsed once on the server, persisted across F5 refreshes, auto-reloaded at 05:00/17:00, and shared across all users.

**Architecture:** Node.js server reads config files from disk, parses them using functions extracted from the existing HTML, stores results in memory, and serves them via REST API. The browser fetches `/api/data` on load instead of requiring manual file drag-drop. Search/filter logic stays in the browser unchanged.

**Tech Stack:** Node.js, Express 4.x, node-cron 3.x, cors 2.x. No database, no build tools.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `package.json` | Create | Node.js project metadata + dependencies |
| `config/settings.json` | Create | Config file paths, port, cron schedule |
| `lib/parser.js` | Create | All parsing functions extracted from HTML (lines 1038–1530) |
| `lib/scheduler.js` | Create | node-cron setup, triggers reload at 05:00/17:00 |
| `server.js` | Create | Express app, in-memory state, loadAllConfigs(), all API routes |
| `public/index.html` | Modify | Copy of NetSearch-prototype.html with fetch-on-load + status bar |
| `cache/parsed.json` | Runtime | Written after each reload; read on server restart |
| `.gitignore` | Create | Ignore cache/ and node_modules/ |

---

## Task 1: Project Scaffold

**Files:**
- Create: `package.json`
- Create: `config/settings.json`
- Create: `.gitignore`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "netsearch",
  "version": "1.0.0",
  "description": "NetSearch backend server",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "node --watch server.js"
  },
  "dependencies": {
    "cors": "^2.8.5",
    "express": "^4.18.2",
    "node-cron": "^3.0.3"
  }
}
```

- [ ] **Step 2: Create config/settings.json**

```bash
mkdir config cache public
```

```json
{
  "port": 3000,
  "configFiles": [
    { "path": "C:/backups/FRI-FW01.conf", "type": "auto" },
    { "path": "C:/backups/FRI-FW02.conf", "type": "auto" }
  ],
  "fqdnFile": "C:/backups/fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

> **Note:** Set `"type": "auto"` to use auto-detection, or `"paloalto"` / `"fortigate"` / `"srx"` / `"f5"` to force a parser. Update `path` values to match actual backup locations.

- [ ] **Step 3: Create .gitignore**

```
node_modules/
cache/
```

- [ ] **Step 4: Install dependencies**

```bash
npm install
```

Expected output: `added N packages` with no errors.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json config/settings.json .gitignore
git commit -m "feat: add Node.js project scaffold for NetSearch backend"
```

---

## Task 2: Extract Parsers to lib/parser.js

**Files:**
- Create: `lib/parser.js`

The parsing functions in `NetSearch-prototype.html` (lines 1038–1530) are pure JavaScript with no browser API dependencies except `genId()` which we include directly.

- [ ] **Step 1: Create lib/parser.js with header and genId**

```bash
mkdir lib
```

Create `lib/parser.js` with this content as the first block:

```javascript
'use strict';
// Parsing functions extracted verbatim from NetSearch-prototype.html
// Lines 1038–1530 of the original file.

// ID generator (mirrors browser-side genId)
let _idCounter = 0;
const genId = () => 'id_' + (++_idCounter) + '_' + Math.random().toString(36).slice(2, 8);
```

- [ ] **Step 2: Append parseValue and all parser functions**

Open `NetSearch-prototype.html`. Copy lines 1038–1530 verbatim (from `const parseValue = ...` through `};` at the end of the auto-detect `parseConfig` function) and append them to `lib/parser.js`.

The block should start with:
```javascript
const parseValue = (str) => { ... };
```
And end with:
```javascript
const parseConfig = (text) => {
  const s=String(text);
  if(s.includes('sys global-settings')||...) return parseF5Config(s);
  ...
  return parsePAConfig(s);
};
```

- [ ] **Step 3: Append module.exports**

At the very end of `lib/parser.js`, add:

```javascript
module.exports = { parseConfig, parsePAConfig, parseFortiGateConfig, parseSRXConfig, parseF5Config, parseFqdnFile };
```

- [ ] **Step 4: Verify parser loads without errors**

```bash
node -e "const p = require('./lib/parser'); console.log(Object.keys(p));"
```

Expected output:
```
[ 'parseConfig', 'parsePAConfig', 'parseFortiGateConfig', 'parseSRXConfig', 'parseF5Config', 'parseFqdnFile' ]
```

- [ ] **Step 5: Quick smoke test with a small config snippet**

```bash
node -e "
const { parseConfig } = require('./lib/parser');
const text = 'set deviceconfig system hostname TEST-FW01';
const result = parseConfig(text);
console.log('type:', result.type, '| hostname:', result.hostname);
"
```

Expected: `type: PA | hostname: TEST-FW01` (or similar — confirms parser runs without crashing)

- [ ] **Step 6: Commit**

```bash
git add lib/parser.js
git commit -m "feat: extract config parsers to lib/parser.js"
```

---

## Task 3: server.js — Phase 1 Core (Load + API)

**Files:**
- Create: `server.js`

- [ ] **Step 1: Create server.js**

```javascript
'use strict';
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { parseConfig, parseFqdnFile } = require('./lib/parser');

const settings = JSON.parse(fs.readFileSync('./config/settings.json', 'utf8'));

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ── In-memory state ──────────────────────────────────────────────────────────
const state = {
  parsedConfigs: [],   // [{ id, filename, parsed }]
  fqdnRecords:   [],   // [{ id, fqdn, domain, ip, owner, type, geoInfo }]
  lastLoaded:    null, // ISO string
  loading:       false,
};

// ── Loader ───────────────────────────────────────────────────────────────────
async function loadAllConfigs() {
  if (state.loading) return { ok: false, error: 'Already loading' };
  state.loading = true;
  console.log('[load] Starting config reload...');
  try {
    const newParsedConfigs = [];

    for (const entry of settings.configFiles) {
      const filePath = entry.path;
      if (!fs.existsSync(filePath)) {
        console.warn(`[load] File not found, skipping: ${filePath}`);
        continue;
      }
      const text = fs.readFileSync(filePath, 'utf8');
      const parsed = parseConfig(text);
      // Fallback hostname from filename if parser couldn't extract one
      if (parsed.hostname && /^Unknown-/.test(parsed.hostname)) {
        const stem = path.basename(filePath)
          .replace(/\.[^.]+$/, '')
          .replace(/[_\-]+config$/i, '')
          .replace(/[_\-]+running$/i, '')
          .trim();
        if (stem) parsed.hostname = stem;
      }
      const id = `cfg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
      newParsedConfigs.push({ id, filename: path.basename(filePath), parsed });
      console.log(`[load] Parsed: ${parsed.hostname} (${parsed.type})`);
    }

    let newFqdnRecords = [];
    if (settings.fqdnFile && fs.existsSync(settings.fqdnFile)) {
      const text = fs.readFileSync(settings.fqdnFile, 'utf8');
      newFqdnRecords = parseFqdnFile(text);
      console.log(`[load] FQDN records: ${newFqdnRecords.length}`);
    }

    // Atomic swap
    state.parsedConfigs = newParsedConfigs;
    state.fqdnRecords   = newFqdnRecords;
    state.lastLoaded    = new Date().toISOString();
    console.log(`[load] Done. ${newParsedConfigs.length} devices loaded.`);
    return { ok: true, lastLoaded: state.lastLoaded };
  } catch (err) {
    console.error('[load] Error:', err.message);
    return { ok: false, error: err.message };
  } finally {
    state.loading = false;
  }
}

// ── API Routes ────────────────────────────────────────────────────────────────
app.get('/api/data', (req, res) => {
  res.json({
    parsedConfigs: state.parsedConfigs,
    fqdnRecords:   state.fqdnRecords,
    lastLoaded:    state.lastLoaded,
  });
});

app.get('/api/status', (req, res) => {
  res.json({
    lastLoaded: state.lastLoaded,
    loading:    state.loading,
    devices: state.parsedConfigs.map(c => ({
      hostname:  c.parsed.hostname,
      type:      c.parsed.type,
      ruleCount: (c.parsed.secRules || []).length,
    })),
  });
});

app.post('/api/reload', async (req, res) => {
  const result = await loadAllConfigs();
  res.json(result);
});

// ── Startup ───────────────────────────────────────────────────────────────────
const PORT = settings.port || 3000;
app.listen(PORT, async () => {
  console.log(`[server] NetSearch running at http://localhost:${PORT}`);
  await loadAllConfigs();
});
```

- [ ] **Step 2: Verify server starts**

```bash
node server.js
```

Expected output (example):
```
[server] NetSearch running at http://localhost:3000
[load] Starting config reload...
[load] Parsed: FRI-FW01 (PA)
[load] Done. 1 devices loaded.
```

If a config file path doesn't exist yet, you'll see `[load] File not found, skipping: ...` — that's fine for now.

- [ ] **Step 3: Verify GET /api/status**

In a second terminal:
```bash
curl http://localhost:3000/api/status
```

Expected:
```json
{"lastLoaded":"2026-04-04T...","loading":false,"devices":[{"hostname":"FRI-FW01","type":"PA","ruleCount":599}]}
```

- [ ] **Step 4: Verify GET /api/data returns parsedConfigs**

```bash
curl http://localhost:3000/api/data | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')); console.log('configs:', d.parsedConfigs.length, '| fqdn:', d.fqdnRecords.length);"
```

Expected: `configs: N | fqdn: M` with N > 0 if config files exist.

- [ ] **Step 5: Commit**

```bash
git add server.js
git commit -m "feat: add Express server with /api/data, /api/status, /api/reload (Phase 1)"
```

---

## Task 4: Frontend — Fetch from Server on Load

**Files:**
- Create: `public/index.html` (copy of NetSearch-prototype.html with modifications)

- [ ] **Step 1: Copy existing HTML to public/**

```bash
cp NetSearch-prototype.html public/index.html
```

- [ ] **Step 2: Add loadFromServer() function**

In `public/index.html`, find the `// ===== EVENT HANDLERS =====` section (near the bottom of the `<script>` block). Add this function just before it:

```javascript
// ── Server integration ────────────────────────────────────────────────────────
async function loadFromServer() {
  const spinner = document.getElementById('searchSpinner');
  const searchInput = document.getElementById('searchInput');
  if (spinner) spinner.classList.add('active');
  if (searchInput) searchInput.disabled = true;
  try {
    const res = await fetch('/api/data');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // Reset and populate state from server
    state.parsedConfigs = data.parsedConfigs || [];
    state.fqdnRecords   = data.fqdnRecords   || [];
    _serverLastLoaded   = data.lastLoaded;
    updateDeviceList();
    updateStatusBar();
    renderContent();
    console.log(`[client] Loaded ${state.parsedConfigs.length} devices from server.`);
  } catch (err) {
    console.error('[client] Failed to load from server:', err.message);
    // Fall through — user can still use drag-drop
  } finally {
    if (spinner) spinner.classList.remove('active');
    if (searchInput) searchInput.disabled = false;
  }
}

let _serverLastLoaded = null;

function updateStatusBar() {
  const el = document.getElementById('serverStatusBar');
  if (!el) return;
  if (_serverLastLoaded) {
    const d = new Date(_serverLastLoaded);
    const fmt = d.toLocaleString('zh-TW', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' });
    el.textContent = `資料版本：${fmt}`;
  } else {
    el.textContent = '尚未載入';
  }
}

async function triggerReload() {
  const btn = document.getElementById('reloadBtn');
  if (btn) { btn.disabled = true; btn.textContent = '重載中...'; }
  try {
    await fetch('/api/reload', { method: 'POST' });
    await loadFromServer();
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🔄 重載'; }
  }
}
```

- [ ] **Step 3: Add status bar HTML**

In `public/index.html`, find the `.header` div. After the logo section, add a status bar element:

```html
<div id="serverStatusBar" style="font-size:11px;color:var(--text-secondary);font-family:var(--font-mono);white-space:nowrap;">載入中...</div>
<button id="reloadBtn" onclick="triggerReload()" class="btn btn-sm" style="font-size:11px;padding:3px 10px;">🔄 重載</button>
```

- [ ] **Step 4: Call loadFromServer() on startup**

In `public/index.html`, find the bottom of the `<script>` block where the app initialises (look for `renderContent()` or `updateDeviceList()` being called at top level). Add `loadFromServer()` call right after:

```javascript
// Auto-load from server on startup
loadFromServer();
```

- [ ] **Step 5: Verify in browser**

Start the server (`node server.js`) then open `http://localhost:3000` in a browser.

Expected behaviour:
- Page loads showing a brief spinner
- Device list populates automatically (no drag-drop needed)
- Status bar shows `資料版本：MM/DD HH:MM`
- F5 re-loads data from server, not from memory

- [ ] **Step 6: Commit**

```bash
git add public/index.html
git commit -m "feat: frontend fetches parsed data from server on load (Phase 1 complete)"
```

---

## Task 5: lib/scheduler.js + Cache (Phase 2)

**Files:**
- Create: `lib/scheduler.js`
- Modify: `server.js` (add cache read/write + cron integration)

- [ ] **Step 1: Create lib/scheduler.js**

```javascript
'use strict';
const cron = require('node-cron');

/**
 * Start cron jobs based on settings.cronSchedule.
 * @param {Function} reloadFn - async function to call on schedule
 * @param {string[]} schedules - array of cron expressions e.g. ["0 5 * * *"]
 */
function startScheduler(reloadFn, schedules) {
  if (!schedules || schedules.length === 0) {
    console.log('[scheduler] No cron schedules configured.');
    return;
  }
  schedules.forEach(expr => {
    if (!cron.validate(expr)) {
      console.error(`[scheduler] Invalid cron expression: ${expr}`);
      return;
    }
    cron.schedule(expr, async () => {
      console.log(`[scheduler] Cron triggered (${expr}), reloading configs...`);
      await reloadFn();
    });
    console.log(`[scheduler] Scheduled reload: ${expr}`);
  });
}

module.exports = { startScheduler };
```

- [ ] **Step 2: Add cache read/write to server.js**

In `server.js`, add these two helper functions right after the `state` object definition:

```javascript
const CACHE_PATH = path.join(__dirname, 'cache', 'parsed.json');

function readCache() {
  try {
    if (fs.existsSync(CACHE_PATH)) {
      const raw = fs.readFileSync(CACHE_PATH, 'utf8');
      const cached = JSON.parse(raw);
      state.parsedConfigs = cached.parsedConfigs || [];
      state.fqdnRecords   = cached.fqdnRecords   || [];
      state.lastLoaded    = cached.lastLoaded     || null;
      console.log(`[cache] Restored ${state.parsedConfigs.length} devices from cache (${state.lastLoaded})`);
    }
  } catch (err) {
    console.warn('[cache] Could not read cache:', err.message);
  }
}

function writeCache() {
  try {
    fs.mkdirSync(path.dirname(CACHE_PATH), { recursive: true });
    fs.writeFileSync(CACHE_PATH, JSON.stringify({
      parsedConfigs: state.parsedConfigs,
      fqdnRecords:   state.fqdnRecords,
      lastLoaded:    state.lastLoaded,
    }), 'utf8');
    console.log('[cache] Cache written.');
  } catch (err) {
    console.warn('[cache] Could not write cache:', err.message);
  }
}
```

- [ ] **Step 3: Call writeCache() after successful load**

In `server.js`, inside `loadAllConfigs()`, find the line:
```javascript
console.log(`[load] Done. ${newParsedConfigs.length} devices loaded.`);
```

Add `writeCache();` immediately after it:
```javascript
console.log(`[load] Done. ${newParsedConfigs.length} devices loaded.`);
writeCache();
return { ok: true, lastLoaded: state.lastLoaded };
```

- [ ] **Step 4: Read cache on startup before fresh load**

In `server.js`, add this require at the **top of the file** alongside the other `require` lines:

```javascript
const { startScheduler } = require('./lib/scheduler');
```

Then find and replace the existing `app.listen` block at the bottom of `server.js` with:

```javascript
const PORT = settings.port || 3000;
app.listen(PORT, async () => {
  console.log(`[server] NetSearch running at http://localhost:${PORT}`);
  // Serve stale cache immediately so first request is instant
  readCache();
  // Then reload from disk in background
  loadAllConfigs();
  // Start cron
  startScheduler(loadAllConfigs, settings.cronSchedule || []);
});
```

- [ ] **Step 5: Verify cache works**

```bash
node server.js
# Ctrl+C after it finishes loading
ls cache/
# Should show: parsed.json
node server.js
# Should show "[cache] Restored N devices" before the fresh load
```

- [ ] **Step 6: Commit**

```bash
git add lib/scheduler.js server.js
git commit -m "feat: add cron scheduler and cache read/write (Phase 2)"
```

---

## Task 6: Final Verification

- [ ] **Step 1: Full end-to-end test**

```bash
node server.js
```

Open `http://localhost:3000` in two different browser tabs simultaneously.

Verify:
- Both tabs show the same device list and rule counts
- F5 in either tab re-loads data without drag-drop
- Status bar shows last loaded time
- `🔄 重載` button triggers reload and updates status bar

- [ ] **Step 2: Test POST /api/reload**

```bash
curl -X POST http://localhost:3000/api/reload
```

Expected:
```json
{"ok":true,"lastLoaded":"2026-04-04T05:00:00.000Z"}
```

- [ ] **Step 3: Test cache recovery**

```bash
# Kill server (Ctrl+C), restart
node server.js
```

Expected first lines:
```
[server] NetSearch running at http://localhost:3000
[cache] Restored N devices from cache (2026-04-04T...)
[load] Starting config reload...
```

Browser should show data instantly (from cache) while fresh load happens in background.

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: NetSearch backend Phase 1+2 complete"
```

---

## Future: Phase 3 (NAS Path)

No code changes needed. When NAS is mounted, update `config/settings.json`:

```json
{
  "configFiles": [
    { "path": "\\\\NAS\\backups\\FRI-FW01.conf", "type": "auto" }
  ]
}
```

Restart server. Node.js `fs.readFileSync` reads UNC paths natively on Windows.

---

## Troubleshooting

| Problem | Check |
|---------|-------|
| `[load] File not found` | Verify paths in `config/settings.json` match actual backup locations |
| Browser shows no data | Open DevTools → Network tab → check `/api/data` response |
| `parsedConfigs` empty after load | Check server terminal for `[load]` lines; ensure config files are readable |
| Cache too large (100MB+ configs) | `cache/parsed.json` may be large; this is expected — it mirrors in-memory state |
