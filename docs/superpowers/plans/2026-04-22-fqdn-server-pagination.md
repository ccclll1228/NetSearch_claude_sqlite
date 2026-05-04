# FQDN Server-Side Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 18,000-record in-memory `state.fqdnRecords` array with a server-side search + pagination API so the browser never holds the full FQDN dataset.

**Architecture:** Two new Express routes (`GET /api/fqdn`, `GET /api/fqdn/meta`) do all filtering/paging server-side. The frontend gets a `state.fqdnPage` sub-object that holds only one page of records (≤ 100 by default). `state.fqdnRecords` is removed entirely; `buildSearchIndex()` always receives `[]` for the FQDN argument.

**Tech Stack:** Node.js / Express (server), Vanilla JS (browser) — no new packages.

---

## Files Modified

| File | Change summary |
|------|---------------|
| `server.js` | Remove fqdnRecords from `/api/data`; add `/api/fqdn` and `/api/fqdn/meta` |
| `public/index.html` | Remove `state.fqdnRecords`; add `state.fqdnPage` + `state.fqdnMeta`; rewrite `renderFqdn()`; add `fetchFqdnMeta()`, `fetchFqdnPage()`; wire up search/filter/pagination |

---

## Task 1: server.js — Remove fqdnRecords from /api/data

**Files:**
- Modify: `server.js:108-114`

- [ ] **Step 1: Edit /api/data response — drop fqdnRecords**

Change `server.js` lines 108-114:

```js
// BEFORE
app.get('/api/data', (req, res) => {
  res.json({
    parsedConfigs: state.parsedConfigs,
    fqdnRecords:   state.fqdnRecords,
    lastLoaded:    state.lastLoaded,
  });
});

// AFTER
app.get('/api/data', (req, res) => {
  res.json({
    parsedConfigs: state.parsedConfigs,
    lastLoaded:    state.lastLoaded,
  });
});
```

- [ ] **Step 2: Verify /api/data no longer contains fqdnRecords**

```bash
curl -s http://localhost:3001/api/data | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));console.log(Object.keys(d));"
# Expected: [ 'parsedConfigs', 'lastLoaded' ]
```

- [ ] **Step 3: Commit**

```bash
git add server.js
git commit -m "feat: remove fqdnRecords from /api/data response"
```

---

## Task 2: server.js — Add GET /api/fqdn/meta

**Files:**
- Modify: `server.js` (insert after `/api/data` route, before `/api/status`)

- [ ] **Step 1: Insert /api/fqdn/meta route**

Add after the `/api/data` handler in `server.js`:

```js
app.get('/api/fqdn/meta', (req, res) => {
  const types  = [...new Set(state.fqdnRecords.map(r => r.type).filter(Boolean))].sort();
  const owners = [...new Set(state.fqdnRecords.map(r => r.owner).filter(Boolean))].sort();
  const geos   = [...new Set(state.fqdnRecords.map(r => r.geoInfo).filter(v => v && v !== 'null' && v !== ''))].sort();
  res.json({ total: state.fqdnRecords.length, types, owners, geos });
});
```

- [ ] **Step 2: Verify /api/fqdn/meta**

```bash
curl -s http://localhost:3001/api/fqdn/meta | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));console.log('total:',d.total,'types:',d.types.length,'owners:',d.owners.length,'geos:',d.geos.length);"
# Expected: total: <N>  types: <X>  owners: <Y>  geos: <Z>  (all numbers, no crash)
```

- [ ] **Step 3: Commit**

```bash
git add server.js
git commit -m "feat: add GET /api/fqdn/meta endpoint"
```

---

## Task 3: server.js — Add GET /api/fqdn (search + pagination)

**Files:**
- Modify: `server.js` (insert after `/api/fqdn/meta`, before `/api/status`)

- [ ] **Step 1: Insert /api/fqdn route**

```js
app.get('/api/fqdn', (req, res) => {
  const q     = (req.query.q     || '').toLowerCase().trim();
  const type  = (req.query.type  || '').trim();
  const owner = (req.query.owner || '').trim();
  const geo   = (req.query.geo   || '').trim();
  const page  = Math.max(1, parseInt(req.query.page, 10) || 1);
  const size  = Math.min(500, Math.max(1, parseInt(req.query.size, 10) || 100));

  let records = state.fqdnRecords;
  if (q)     records = records.filter(r => (r.fqdn  || '').toLowerCase().includes(q) ||
                                           (r.domain|| '').toLowerCase().includes(q) ||
                                           (r.ip    || '').toLowerCase().includes(q) ||
                                           (r.owner || '').toLowerCase().includes(q));
  if (type)  records = records.filter(r => r.type    === type);
  if (owner) records = records.filter(r => r.owner   === owner);
  if (geo)   records = records.filter(r => r.geoInfo === geo);

  const total = records.length;
  const start = (page - 1) * size;
  res.json({ total, page, size, records: records.slice(start, start + size) });
});
```

- [ ] **Step 2: Verify /api/fqdn pagination**

```bash
# Page 1, default size
curl -s "http://localhost:3001/api/fqdn?page=1&size=5" | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));console.log('total:',d.total,'page:',d.page,'size:',d.size,'records:',d.records.length);"
# Expected: total: <N>  page: 1  size: 5  records: 5

# Keyword search
curl -s "http://localhost:3001/api/fqdn?q=google&size=5" | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));console.log('total:',d.total,'records:',d.records.length);"
# Expected: total: <some subset>  records: ≤5
```

- [ ] **Step 3: Commit**

```bash
git add server.js
git commit -m "feat: add GET /api/fqdn search+pagination endpoint"
```

---

## Task 4: index.html — State object changes

**Files:**
- Modify: `public/index.html:2603-2629`

- [ ] **Step 1: Remove fqdnRecords, fqdnTypeFilter/OwnerFilter/GeoFilter; add fqdnPage + fqdnMeta**

Find and replace the state object initialisation. The block starts at line 2603 (`let state = {`).

Change `fqdnRecords: [],` (line 2606) → remove it entirely.

Add after `searchIndex: null,`:
```js
fqdnMeta: null,
fqdnPage: { records: [], total: 0, page: 1, size: 100, loading: false, q: '', type: '', owner: '', geo: '' },
```

Remove from `filters` object (line 2627):
```js
fqdnTypeFilter: '', fqdnOwnerFilter: '', fqdnGeoFilter: '',
```

Also remove `forceShowFqdn: false,` (line 2616) — it's replaced by checking `state.fqdnPage.records.length`.

- [ ] **Step 2: Fix clearAllFilters() — remove fqdnTypeFilter/OwnerFilter/GeoFilter**

Find `clearAllFilters()` at line ~5731. Remove `fqdnTypeFilter: '', fqdnOwnerFilter: '', fqdnGeoFilter: ''` from the `state.filters` reset object.

After the filters reset line, add:
```js
state.fqdnPage.q = ''; state.fqdnPage.type = ''; state.fqdnPage.owner = ''; state.fqdnPage.geo = ''; state.fqdnPage.page = 1;
```

- [ ] **Step 3: Fix clearAllFqdn() — reset fqdnPage instead of fqdnRecords**

Find `clearAllFqdn()` at line ~5967. Replace body:

```js
// BEFORE
state.fqdnRecords = []; state.forceShowFqdn = false;
updateDeviceList(); renderContent();

// AFTER
state.fqdnPage = { records: [], total: 0, page: 1, size: 100, loading: false, q: '', type: '', owner: '', geo: '' };
state.fqdnMeta = null;
renderContent();
```

- [ ] **Step 4: No verification needed (state changes won't break JS until we update callers)**

---

## Task 5: index.html — Update all state.fqdnRecords references

**Files:**
- Modify: `public/index.html` (multiple locations)

- [ ] **Step 1: getFilteredData() — replace state.fqdnRecords with empty array**

At line ~3705, change:
```js
// BEFORE
const fqdnRecords = state.fqdnRecords;

// AFTER
const fqdnRecords = [];
```

This disables FQDN→IP cross-tab chaining (accepted trade-off to eliminate OOM).

- [ ] **Step 2: buildSearchIndex() call sites — pass [] instead of state.fqdnRecords**

Four call sites exist. In each, replace `state.fqdnRecords` argument with `[]`:

Line ~5551 in `loadFromServer()`:
```js
state.searchIndex = buildSearchIndex(state.parsedConfigs, []);
```

Line ~5943 in `addConfig()`:
```js
state.searchIndex = buildSearchIndex(state.parsedConfigs, []);
```

Line ~5954 in `removeConfig()`:
```js
state.searchIndex = buildSearchIndex(state.parsedConfigs, []);
```

Line ~5962 in `clearAllConfigs()`:
```js
state.searchIndex = buildSearchIndex([], []);
```

- [ ] **Step 3: Drag-drop FQDN import functions — neuter push to state.fqdnRecords**

`importStagedFqdn()` (~line 5805): remove `state.fqdnRecords.push(...records);` line. Keep rest of function.

`handleFqdnFiles()` (~line 5837): remove `state.fqdnRecords.push(...records);` line. Keep rest of function.

- [ ] **Step 4: updateDeviceList() — remove FQDN count from device list**

Find lines ~5984-5986:
```js
if (state.fqdnRecords.length > 0) {
  html += `<div class="device-item">...<b>${T('devFqdnRecords', state.fqdnRecords.length)}</b>...`;
}
```

Replace with:
```js
if (state.fqdnMeta && state.fqdnMeta.total > 0) {
  html += `<div class="device-item"><div><span class="device-type" style="background:#ECFDF5;color:#16A34A">FQDN</span> <b>${T('devFqdnRecords', state.fqdnMeta.total)}</b></div></div>`;
}
```

- [ ] **Step 5: Verify no remaining state.fqdnRecords references**

```bash
grep -n "state\.fqdnRecords" /home/local/SSO/yt0115/NetSearch_claude/public/index.html
# Expected: zero matches
```

- [ ] **Step 6: Commit**

```bash
git add public/index.html
git commit -m "refactor: replace state.fqdnRecords with fqdnPage/fqdnMeta"
```

---

## Task 6: index.html — Add fetchFqdnMeta() and fetchFqdnPage()

**Files:**
- Modify: `public/index.html` (insert new functions after `loadFromServer()`, around line ~5563)

- [ ] **Step 1: Add fetchFqdnMeta() after loadFromServer()**

Insert after the closing `}` of `loadFromServer()`:

```js
async function fetchFqdnMeta() {
  try {
    const res = await fetch('/api/fqdn/meta');
    if (!res.ok) return;
    state.fqdnMeta = await res.json();
    updateDeviceList();
    renderTabs();
  } catch (err) {
    console.error('[client] fetchFqdnMeta failed:', err.message);
  }
}
```

- [ ] **Step 2: Add fetchFqdnPage() immediately after fetchFqdnMeta()**

```js
async function fetchFqdnPage(resetPage) {
  if (resetPage) state.fqdnPage.page = 1;
  state.fqdnPage.loading = true;
  const { q, type, owner, geo, page, size } = state.fqdnPage;
  const params = new URLSearchParams();
  if (q)     params.set('q', q);
  if (type)  params.set('type', type);
  if (owner) params.set('owner', owner);
  if (geo)   params.set('geo', geo);
  params.set('page', page);
  params.set('size', size);
  try {
    const res = await fetch('/api/fqdn?' + params.toString());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.fqdnPage.records = data.records;
    state.fqdnPage.total   = data.total;
    state.fqdnPage.page    = data.page;
    state.fqdnPage.size    = data.size;
  } catch (err) {
    console.error('[client] fetchFqdnPage failed:', err.message);
  } finally {
    state.fqdnPage.loading = false;
  }
  if (state.activeTab === 'fqdn') {
    document.getElementById('content').innerHTML = renderFqdn();
  }
}
```

- [ ] **Step 3: Wire fetchFqdnMeta() call after server data load**

In `loadFromServer()`, after `renderContent();` call (~line 5555), add:
```js
fetchFqdnMeta();
```

- [ ] **Step 4: Commit**

```bash
git add public/index.html
git commit -m "feat: add fetchFqdnMeta and fetchFqdnPage async functions"
```

---

## Task 7: index.html — Rewrite renderFqdn()

**Files:**
- Modify: `public/index.html:4959-5008`

- [ ] **Step 1: Replace renderFqdn() entirely**

The current `renderFqdn(list)` signature and body (lines 4960-5008) should be replaced with:

```js
function renderFqdn() {
  const pg   = state.fqdnPage;
  const meta = state.fqdnMeta;
  const records = pg.records;

  // Build filter dropdowns from meta
  const types  = meta ? meta.types  : [];
  const owners = meta ? meta.owners : [];
  const geos   = meta ? meta.geos   : [];

  const filterHtml = `<div class="flex gap-2 items-center mb-2" style="flex-wrap:wrap">
    <select class="filter-select" onchange="state.fqdnPage.type=this.value;fetchFqdnPage(true)"><option value="">Type (All)</option>${types.map(t => `<option value="${esc(t)}" ${pg.type === t ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select>
    <select class="filter-select" onchange="state.fqdnPage.owner=this.value;fetchFqdnPage(true)"><option value="">Owner (All)</option>${owners.map(o => `<option value="${esc(o)}" ${pg.owner === o ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>
    <select class="filter-select" onchange="state.fqdnPage.geo=this.value;fetchFqdnPage(true)"><option value="">Geo (All)</option>${geos.map(g => `<option value="${esc(g)}" ${pg.geo === g ? 'selected' : ''}>${esc(g)}</option>`).join('')}</select>
  </div>`;

  // Prompt state: no records loaded yet and no active filter
  if (records.length === 0 && !pg.q && !pg.type && !pg.owner && !pg.geo) {
    const totalLabel = meta ? meta.total : 0;
    return filterHtml + `<div class="empty-state"><p>${T('fqdnPrompt')}</p><button class="btn btn-primary mt-2" onclick="state.fqdnPage.q='';fetchFqdnPage(true)">${T('fqdnShowAll', totalLabel)}</button></div>`;
  }

  if (records.length === 0) return filterHtml + `<div class="empty-state">${T('noFqdn')}</div>`;

  const sorted = [...records].sort((a, b) => smartSort(a, b, fqdnSortState.key, fqdnSortState.dir));
  _lastFilteredFqdnRows = sorted;
  const arrow = (k) => fqdnSortState.key === k ? `<span class="sort-arrow">${fqdnSortState.dir === 'asc' ? '▲' : '▼'}</span>` : '';
  const colPickerHtml = FQDN_COPY_FIELDS.map((f, i) => `<label style="display:flex;align-items:center;gap:6px;padding:3px 0;cursor:pointer;font-size:12px;color:var(--text)"><input type="checkbox" ${f.selected ? 'checked' : ''} onchange="FQDN_COPY_FIELDS[${i}].selected=this.checked" style="accent-color:var(--accent);cursor:pointer">${f.label}</label>`).join('');

  const totalPages = Math.ceil(pg.total / pg.size) || 1;
  const paginationHtml = `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;font-size:12px;font-family:var(--cds-font-mono)">
    <button class="btn btn-sm" id="fqdnPrevBtn" ${pg.page <= 1 ? 'disabled' : ''} onclick="state.fqdnPage.page--;fetchFqdnPage(false)">‹ Prev</button>
    <span id="fqdnPageInfo">Page ${pg.page} / ${totalPages}  —  ${pg.total} records total</span>
    <button class="btn btn-sm" id="fqdnNextBtn" ${pg.page * pg.size >= pg.total ? 'disabled' : ''} onclick="state.fqdnPage.page++;fetchFqdnPage(false)">Next ›</button>
  </div>`;

  return filterHtml +
    `<div class="stats-bar" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">${T('statsFqdn', pg.total)}<details style="position:relative;display:inline-block"><summary style="list-style:none;cursor:pointer;padding:2px 7px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:11px;color:var(--text-muted);background:var(--bg-card)">Copy Columns ▾</summary><div style="position:absolute;top:calc(100% + 4px);left:0;z-index:300;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:8px 12px;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,.4)">${colPickerHtml}</div></details><button class="rule-copy-btn" onclick="copyFqdnTSV()" title="Copy filtered results as TSV">${SVG_COPY} Copy</button></div>
    <table class="fqdn-table"><colgroup><col style="width:7%"><col style="width:13%"><col style="width:28%"><col style="width:11%"><col style="width:16%"><col style="width:8%"><col style="width:17%"></colgroup><thead><tr>
      <th onclick="sortFqdn('owner')">Owner${arrow('owner')}</th>
      <th onclick="sortFqdn('domain')">Domain${arrow('domain')}</th>
      <th onclick="sortFqdn('fqdn')">FQDN${arrow('fqdn')}</th>
      <th onclick="sortFqdn('type')">Type${arrow('type')}</th>
      <th onclick="sortFqdn('ip')">IP${arrow('ip')}</th>
      <th onclick="sortFqdn('geoInfo')">Geo${arrow('geoInfo')}</th>
      <th></th>
    </tr></thead><tbody>${sorted.map(r => { const d = stripDot(r.domain), fq = stripDot(r.fqdn), ip = stripDot(r.ip); return `<tr${r._chainedFromRule ? ' style="border-left:3px solid var(--yellow)"' : ''}><td>${esc(r.owner)}</td><td>${esc(d)}<button class="pill-qs" onclick="event.stopPropagation();quickSearch('${esc(d)}')" title="Search">${SVG_QS}</button></td><td>${esc(fq)}<button class="pill-qs" onclick="event.stopPropagation();quickSearch('${esc(fq)}')" title="Search">${SVG_QS}</button></td><td>${esc(r.type)}</td><td>${esc(ip)}<button class="pill-qs" onclick="event.stopPropagation();quickSearch('${esc(ip)}')" title="Search">${SVG_QS}</button></td><td>${esc(r.geoInfo)}</td><td></td></tr>`; }).join('')}</tbody></table>` +
    paginationHtml;
}
```

- [ ] **Step 2: Fix renderFqdn() call site in renderContent()**

At line ~4246, change:
```js
// BEFORE
case 'fqdn': el.innerHTML = renderFqdn(d.fqdnList); break;

// AFTER
case 'fqdn': el.innerHTML = renderFqdn(); break;
```

- [ ] **Step 3: Fix renderTabs() — fqdn tab count from fqdnMeta**

At line ~4192, change:
```js
// BEFORE
f5_pools: d.f5Pools.length, fqdn: d.fqdnList.length, copy: '', raw: '', debug: ''

// AFTER
f5_pools: d.f5Pools.length, fqdn: (state.fqdnMeta ? state.fqdnMeta.total : ''), copy: '', raw: '', debug: ''
```

- [ ] **Step 4: Fix sortFqdn() — remove renderContent() call, call renderFqdn() directly**

At line ~5623:
```js
// BEFORE
function sortFqdn(key) { if (fqdnSortState.key === key) fqdnSortState.dir = fqdnSortState.dir === 'asc' ? 'desc' : 'asc'; else { fqdnSortState.key = key; fqdnSortState.dir = 'asc'; } renderContent(); }

// AFTER
function sortFqdn(key) { if (fqdnSortState.key === key) fqdnSortState.dir = fqdnSortState.dir === 'asc' ? 'desc' : 'asc'; else { fqdnSortState.key = key; fqdnSortState.dir = 'asc'; } if (state.activeTab === 'fqdn') document.getElementById('content').innerHTML = renderFqdn(); }
```

- [ ] **Step 5: Commit**

```bash
git add public/index.html
git commit -m "feat: rewrite renderFqdn() with server pagination controls"
```

---

## Task 8: index.html — Wire global search Enter key for FQDN tab

**Files:**
- Modify: `public/index.html:6148-6167`

- [ ] **Step 1: Update search Enter handler to dispatch to fetchFqdnPage when on FQDN tab**

Find the `searchInput` keydown listener (~line 6148):

```js
// BEFORE (inside the if (e.key === 'Enter') block, after setting state.searchAST):
renderContent();

// AFTER (replace the renderContent() call with):
if (state.activeTab === 'fqdn') {
  state.fqdnPage.q = query;
  fetchFqdnPage(true);
} else {
  renderContent();
}
```

Keep all other lines in the handler (`state.search = query`, `state.appliedSearch = query`, `state.searchAST = parseSearch(query)`, history, spinner) unchanged.

- [ ] **Step 2: Commit**

```bash
git add public/index.html
git commit -m "feat: wire global search Enter to fetchFqdnPage when on FQDN tab"
```

---

## Task 9: Manual smoke test + final commit

- [ ] **Step 1: Restart server**

```bash
pkill -f "node server.js" || true
node server.js > /tmp/server.log 2>&1 &
sleep 6
grep "\[load\]" /tmp/server.log | tail -5
```

- [ ] **Step 2: Verify /api/data no longer contains fqdnRecords key**

```bash
curl -s http://localhost:3001/api/data | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));const keys=Object.keys(d);console.log('keys:',keys);console.assert(!keys.includes('fqdnRecords'),'FAIL: fqdnRecords still in /api/data');"
# Expected: keys: [ 'parsedConfigs', 'lastLoaded' ]
```

- [ ] **Step 3: Verify /api/fqdn/meta**

```bash
curl -s http://localhost:3001/api/fqdn/meta | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));console.log(JSON.stringify(d,null,2));" | head -10
# Expected: { total: <N>, types: [...], owners: [...], geos: [...] }
```

- [ ] **Step 4: Verify /api/fqdn pagination**

```bash
curl -s "http://localhost:3001/api/fqdn?page=1&size=3" | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));console.log('total:',d.total,'records:',d.records.length);console.assert(d.records.length===3,'FAIL: expected 3 records');"
# Expected: total: <N>  records: 3

curl -s "http://localhost:3001/api/fqdn?q=google&size=5" | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));console.log('q=google total:',d.total,'records:',d.records.length);"
```

- [ ] **Step 5: Browser smoke test**

Open http://localhost:3001 in browser:
1. FQDN tab badge shows total count (e.g. 18,453) — from fqdnMeta
2. FQDN tab body shows prompt with "Show All FQDN (18,453 records)" button
3. Click "Show All FQDN" → records load, pagination controls appear (Page 1 / N — total records)
4. Click "Next ›" → page 2 loads
5. Click "Prev ›" disabled on page 1, enabled on page 2
6. Type "google" in search bar and press Enter while on FQDN tab → filtered results appear
7. Filter dropdowns (Type, Owner, Geo) populated and functional
8. Switch to Sec Rules tab → search still works normally (FQDN chaining gone but no crash)

- [ ] **Step 6: Final push**

```bash
git push origin main
```

---

## Spec Coverage Checklist

| Spec requirement | Task |
|-----------------|------|
| Remove fqdnRecords from /api/data | Task 1 |
| GET /api/fqdn with q/type/owner/geo/page/size | Task 3 |
| GET /api/fqdn/meta with types/owners/geos | Task 2 |
| Remove fqdnRecords: [] from state | Task 4 |
| Add fqdnPage sub-state | Task 4 |
| /api/data fetch handler: remove fqdnRecords | Task 5 |
| fetchFqdnMeta() called after data load | Task 6 |
| fetchFqdnMeta() updates FQDN tab count badge | Task 6 + Task 7 step 3 |
| fetchFqdnPage(resetPage) built and wired | Task 6 |
| renderFqdn() reads from state.fqdnPage.records | Task 7 |
| Remove 2000-record client-side cap | Task 7 |
| Pagination controls (Prev/Next + page info) | Task 7 |
| Filter selects use fqdnMeta for options | Task 7 |
| Filter select onchange calls fetchFqdnPage(true) | Task 7 |
| Global search Enter on FQDN tab → fetchFqdnPage(true) | Task 8 |
| "Show All FQDN" button calls fetchFqdnPage(true) | Task 7 |
| Remove every state.fqdnRecords reference | Task 5 |
| buildSearchIndex() gets [] for fqdnRecords | Task 5 |
