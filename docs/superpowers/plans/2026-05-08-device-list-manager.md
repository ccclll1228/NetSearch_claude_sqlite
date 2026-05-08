# Device List Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Server Config tab to the Import modal so users can view, add, edit, and delete devices and persist changes to `config/settings.json` without SSH access.

**Architecture:** Two new API endpoints in `server.js`; tab bar + `devMgr` state + render/edit functions in `public/index.html`; `deviceTypes` field added to `settings.example.json`. No other files touched.

**Tech Stack:** Express (server.js), vanilla JS (index.html), `fs.readFileSync`/`fs.writeFileSync`.

---

### Task 1: Backend — `GET /api/settings` and `POST /api/settings`

**Files:**
- Modify: `server.js` (after the existing `POST /api/reload` route, before `// ── Startup`)

- [ ] **Step 1: Add the two routes**

Insert after the `app.post('/api/reload', ...)` block and before the `// ── Startup` comment:

```js
app.get('/api/settings', (req, res) => {
  try {
    const s = JSON.parse(fs.readFileSync('./config/settings.json', 'utf8'));
    res.json({
      backupRoot:  s.backupRoot  || '',
      devices:     s.devices     || [],
      deviceTypes: s.deviceTypes || ['paloalto', 'f5', 'fortigate', 'srx'],
    });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/api/settings', (req, res) => {
  const { backupRoot, devices, deviceTypes } = req.body || {};
  if (!backupRoot || typeof backupRoot !== 'string' || !backupRoot.trim())
    return res.status(400).json({ ok: false, error: 'backupRoot is required' });
  if (!Array.isArray(devices))
    return res.status(400).json({ ok: false, error: 'devices must be an array' });
  for (const d of devices) {
    if (!d.name || !String(d.name).trim())
      return res.status(400).json({ ok: false, error: 'Each device must have a non-empty name' });
    if (!d.type || !String(d.type).trim())
      return res.status(400).json({ ok: false, error: `Device "${d.name}" must have a type` });
  }
  const names = devices.map(d => String(d.name).trim().toLowerCase());
  if (new Set(names).size !== names.length)
    return res.status(400).json({ ok: false, error: 'Duplicate device names are not allowed' });
  if (!Array.isArray(deviceTypes) || deviceTypes.length === 0)
    return res.status(400).json({ ok: false, error: 'deviceTypes must have at least one entry' });
  for (const t of deviceTypes)
    if (!t || !String(t).trim())
      return res.status(400).json({ ok: false, error: 'Device type cannot be empty' });
  try {
    const current = JSON.parse(fs.readFileSync('./config/settings.json', 'utf8'));
    const updated = {
      ...current,
      backupRoot:  backupRoot.trim(),
      devices:     devices.map(d => ({ name: String(d.name).trim(), type: String(d.type).trim() })),
      deviceTypes: deviceTypes.map(t => String(t).trim()),
    };
    fs.writeFileSync('./config/settings.json', JSON.stringify(updated, null, 2), 'utf8');
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});
```

- [ ] **Step 2: Verify with curl (server must be running)**

```bash
curl -s http://localhost:3002/api/settings | python3 -m json.tool
```

Expected: JSON with `backupRoot`, `devices`, `deviceTypes`.

- [ ] **Step 3: Commit**

```bash
git add server.js
git commit -m "feat: add GET/POST /api/settings endpoints"
```

---

### Task 2: `settings.example.json` — add `deviceTypes`

**Files:**
- Modify: `config/settings.example.json`

- [ ] **Step 1: Add `deviceTypes` field between `devices` and `cronSchedule`**

```json
  "deviceTypes": ["paloalto", "f5", "fortigate", "srx"],
```

- [ ] **Step 2: Commit**

```bash
git add config/settings.example.json
git commit -m "feat: add deviceTypes field to settings.example.json"
```

---

### Task 3: CSS — device manager styles

**Files:**
- Modify: `public/index.html` (after `.hidden { display: none; }` block, around line 2209)

- [ ] **Step 1: Insert styles after `.hidden { display: none; }`**

```css
    /* ── Device Manager tabs ── */
    .devmgr-tabs { display:flex; border-bottom:1px solid var(--cds-border-subtle); margin-bottom:12px; }
    .devmgr-tab  { flex:none; padding:6px 16px; font-size:12px; font-family:var(--cds-font-sans);
                   background:none; border:none; border-bottom:2px solid transparent;
                   cursor:pointer; color:var(--cds-text-secondary); }
    .devmgr-tab.active { color:var(--cds-text-primary); border-bottom-color:var(--cds-interactive); font-weight:600; }
    .devmgr-tab:hover:not(.active) { background:var(--cds-layer-hover); }
    .devmgr-table { width:100%; border-collapse:collapse; font-size:12px; margin:4px 0; }
    .devmgr-table th { background:var(--cds-layer-02); padding:5px 8px; text-align:left; font-weight:600; font-size:11px; border-bottom:1px solid var(--cds-border-subtle); }
    .devmgr-table td { padding:5px 8px; border-bottom:1px solid var(--cds-border-subtle); vertical-align:middle; }
    .devmgr-table tr:last-child td { border-bottom:none; }
    .devmgr-type-chip { display:inline-flex; align-items:center; gap:3px; padding:2px 8px; background:var(--cds-layer-02); border:1px solid var(--cds-border-subtle); font-size:11px; margin:2px; }
    .devmgr-type-chip .chip-del { background:none; border:none; cursor:pointer; color:var(--cds-text-secondary); padding:0 2px; font-size:13px; line-height:1; }
    .devmgr-type-chip .chip-del:hover:not(:disabled) { color:var(--cds-support-error); }
    .devmgr-type-chip .chip-del:disabled { opacity:0.35; cursor:not-allowed; }
    .devmgr-status { font-size:12px; margin-left:12px; color:var(--cds-text-secondary); }
    .devmgr-status.error { color:var(--cds-support-error); }
```

- [ ] **Step 2: Commit**

```bash
git add public/index.html
git commit -m "feat: add device manager CSS styles"
```

---

### Task 4: i18n — new keys

**Files:**
- Modify: `public/index.html` — `en` object (before its closing `},`) and `zh` object (before its closing `}`)

- [ ] **Step 1: Add keys to `en` object (after the last key `truncated: '... (truncated)',`)**

```js
        tabImport: 'Import', tabServerConfig: 'Server Config',
        devMgrBackupRoot: 'Backup Root Directory',
        devMgrDevices: 'Devices', devMgrAddDevice: '＋ Add Device',
        devMgrDeviceTypes: 'Device Types', devMgrAddType: 'Add',
        devMgrEdit: 'Edit', devMgrDelete: 'Delete',
        devMgrSaveRow: 'Save', devMgrCancel: 'Cancel',
        devMgrSaveReload: 'Save & Reload',
        devMgrSaving: 'Saving…', devMgrReloading: 'Reloading…',
        devMgrDone: 'Done. {0} device(s) loaded.',
        devMgrInUse: 'In use',
        devMgrErrEmpty: 'Name and type cannot be empty.',
        devMgrErrDupe: 'Duplicate device name.',
```

- [ ] **Step 2: Add keys to `zh` object (after the last key `truncated: '... （已截斷）',`)**

```js
        tabImport: '匯入', tabServerConfig: '伺服器設定',
        devMgrBackupRoot: '備份根目錄',
        devMgrDevices: '設備列表', devMgrAddDevice: '＋ 新增設備',
        devMgrDeviceTypes: '設備類型', devMgrAddType: '新增',
        devMgrEdit: '編輯', devMgrDelete: '刪除',
        devMgrSaveRow: '儲存', devMgrCancel: '取消',
        devMgrSaveReload: '儲存並重載',
        devMgrSaving: '儲存中…', devMgrReloading: '重載中…',
        devMgrDone: '完成。已載入 {0} 台設備。',
        devMgrInUse: '使用中',
        devMgrErrEmpty: '名稱與類型不可為空。',
        devMgrErrDupe: '設備名稱重複。',
```

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat: add device manager i18n keys"
```

---

### Task 5: HTML — add tab bar and wrap modal body content

**Files:**
- Modify: `public/index.html` — inside `#importModal .modal-body`

The current `<div class="modal-body">` starts with `<!-- Imported Devices -->` and ends just before its closing `</div>`. We need to:
1. Insert the tab bar immediately after `<div class="modal-body">`
2. Wrap all existing content in `<div id="importTabImport">`
3. Add `<div id="importTabServerConfig" class="hidden"></div>` after

- [ ] **Step 1: Replace the opening of modal-body to add tab bar + wrapper open tag**

Find:
```html
      <div class="modal-body">
        <!-- Imported Devices -->
        <div class="device-list" id="deviceList"></div>
```

Replace with:
```html
      <div class="modal-body">
        <div class="devmgr-tabs" id="importTabBar">
          <button class="devmgr-tab active" id="tabImport" onclick="switchImportTab('import')">Import</button>
          <button class="devmgr-tab" id="tabServerConfig" onclick="switchImportTab('serverConfig')">Server Config</button>
        </div>
        <div id="importTabImport">
        <!-- Imported Devices -->
        <div class="device-list" id="deviceList"></div>
```

- [ ] **Step 2: Close `#importTabImport` and add `#importTabServerConfig` before the modal-body closing tag**

Find:
```html
        <div style="margin-top:16px;display:flex;gap:8px">
          <button class="btn btn-sm btn-danger" id="btnClearConfigs" onclick="clearAllConfigs()">Clear All
            Configs</button>
          <button class="btn btn-sm btn-danger" id="btnClearFqdn" onclick="clearAllFqdn()">Clear FQDN</button>
        </div>
      </div>
    </div>
  </div>
```

Replace with:
```html
        <div style="margin-top:16px;display:flex;gap:8px">
          <button class="btn btn-sm btn-danger" id="btnClearConfigs" onclick="clearAllConfigs()">Clear All
            Configs</button>
          <button class="btn btn-sm btn-danger" id="btnClearFqdn" onclick="clearAllFqdn()">Clear FQDN</button>
        </div>
        </div><!-- end #importTabImport -->
        <div id="importTabServerConfig" class="hidden"></div>
      </div>
    </div>
  </div>
```

- [ ] **Step 3: Verify HTML structure is valid (open the page and check the Import modal opens)**

- [ ] **Step 4: Commit**

```bash
git add public/index.html
git commit -m "feat: add tab bar to import modal"
```

---

### Task 6: JS — `devMgr` state and all functions

**Files:**
- Modify: `public/index.html` — insert after `function closeImportModal() { ... }` (around line 6421)

- [ ] **Step 1: Insert the full device manager JS block**

```js
    // ── Device Manager ────────────────────────────────────────────────────────
    const devMgr = { backupRoot: '', devices: [], deviceTypes: [], editingIdx: -1 };

    function switchImportTab(name) {
      document.getElementById('importTabImport').classList.toggle('hidden', name !== 'import');
      document.getElementById('importTabServerConfig').classList.toggle('hidden', name !== 'serverConfig');
      document.getElementById('tabImport').classList.toggle('active', name === 'import');
      document.getElementById('tabServerConfig').classList.toggle('active', name === 'serverConfig');
      if (name === 'serverConfig' && devMgr.devices.length === 0) loadDevMgr();
    }

    async function loadDevMgr() {
      const panel = document.getElementById('importTabServerConfig');
      panel.innerHTML = '<div style="padding:16px;color:var(--cds-text-secondary);font-size:12px">Loading…</div>';
      try {
        const data = await fetch('/api/settings').then(r => r.json());
        devMgr.backupRoot  = data.backupRoot  || '';
        devMgr.devices     = (data.devices    || []).map(d => ({ ...d }));
        devMgr.deviceTypes = data.deviceTypes || ['paloalto', 'f5', 'fortigate', 'srx'];
        devMgr.editingIdx  = -1;
        renderDevMgr();
      } catch (err) {
        panel.innerHTML = `<div style="padding:16px;color:var(--cds-support-error);font-size:12px">Failed to load settings: ${esc(err.message)}</div>`;
      }
    }

    function renderDevMgr() {
      const inUseTypes = new Set(devMgr.devices.map(d => d.type));
      const rows = devMgr.devices.map((d, i) => {
        if (i === devMgr.editingIdx) {
          const opts = devMgr.deviceTypes.map(t =>
            `<option value="${esc(t)}"${t === d.type ? ' selected' : ''}>${esc(t)}</option>`).join('');
          return `<tr>
            <td><input id="devMgrEditName" value="${esc(d.name)}"
              style="width:100%;padding:3px 6px;border:1px solid var(--cds-focus);font-size:12px;font-family:var(--cds-font-mono);box-sizing:border-box"></td>
            <td><select id="devMgrEditType" style="padding:3px 6px;font-size:12px">${opts}</select></td>
            <td style="white-space:nowrap">
              <button class="btn btn-sm btn-primary" onclick="saveDevRow(${i})">${T('devMgrSaveRow')}</button>
              <button class="btn btn-sm" onclick="cancelDevRow()" style="margin-left:4px">${T('devMgrCancel')}</button>
            </td></tr>`;
        }
        return `<tr>
          <td style="font-family:var(--cds-font-mono);font-size:12px">${esc(d.name)}</td>
          <td style="font-size:12px">${esc(d.type)}</td>
          <td style="white-space:nowrap">
            <button class="btn btn-sm" onclick="editDevRow(${i})">${T('devMgrEdit')}</button>
            <button class="btn btn-sm" onclick="deleteDevRow(${i})" style="color:var(--cds-support-error);margin-left:4px">${T('devMgrDelete')}</button>
          </td></tr>`;
      }).join('');

      const chips = devMgr.deviceTypes.map((t, i) => {
        const inUse = inUseTypes.has(t);
        return `<span class="devmgr-type-chip">${esc(t)}<button class="chip-del" onclick="deleteDevType(${i})"${inUse ? ` disabled title="${T('devMgrInUse')}"` : ''}>×</button></span>`;
      }).join('');

      document.getElementById('importTabServerConfig').innerHTML = `
        <div style="margin-bottom:12px">
          <label style="display:block;font-size:11px;font-weight:600;margin-bottom:4px;color:var(--cds-text-secondary)">${T('devMgrBackupRoot')}</label>
          <input id="devMgrBackupRoot" value="${esc(devMgr.backupRoot)}"
            style="width:100%;padding:6px 8px;border:none;border-bottom:1px solid var(--cds-border-subtle);background:var(--cds-layer-01);font-size:12px;font-family:var(--cds-font-mono);box-sizing:border-box"
            oninput="devMgr.backupRoot=this.value">
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
          <span style="font-size:11px;font-weight:600;color:var(--cds-text-secondary)">${T('devMgrDevices')}</span>
          <button class="btn btn-sm" onclick="addDevRow()">${T('devMgrAddDevice')}</button>
        </div>
        <table class="devmgr-table">
          <thead><tr><th>Name</th><th>Type</th><th>Actions</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <div style="margin-top:12px">
          <div style="font-size:11px;font-weight:600;color:var(--cds-text-secondary);margin-bottom:6px">${T('devMgrDeviceTypes')}</div>
          <div style="margin-bottom:6px">${chips}</div>
          <div style="display:flex;gap:6px;align-items:center">
            <input id="devMgrNewType" placeholder="new type"
              style="padding:4px 6px;border:1px solid var(--cds-border-subtle);font-size:12px;width:120px"
              onkeydown="if(event.key==='Enter'){event.preventDefault();addDevType();}">
            <button class="btn btn-sm" onclick="addDevType()">${T('devMgrAddType')}</button>
          </div>
        </div>
        <div style="margin-top:16px;display:flex;align-items:center">
          <button class="btn btn-primary btn-sm" onclick="saveDevMgr()">${T('devMgrSaveReload')}</button>
          <span class="devmgr-status" id="devMgrStatus"></span>
        </div>`;
    }

    function editDevRow(i)   { devMgr.editingIdx = i; renderDevMgr(); }
    function cancelDevRow()  { devMgr.editingIdx = -1; renderDevMgr(); }

    function saveDevRow(i) {
      const name = (document.getElementById('devMgrEditName').value || '').trim();
      const type = (document.getElementById('devMgrEditType').value || '').trim();
      if (!name || !type) { alert(T('devMgrErrEmpty')); return; }
      const dup = devMgr.devices.some((d, idx) => idx !== i && d.name.toLowerCase() === name.toLowerCase());
      if (dup) { alert(T('devMgrErrDupe')); return; }
      devMgr.devices[i] = { name, type };
      devMgr.editingIdx = -1;
      renderDevMgr();
    }

    function addDevRow() {
      devMgr.devices.push({ name: '', type: devMgr.deviceTypes[0] || '' });
      devMgr.editingIdx = devMgr.devices.length - 1;
      renderDevMgr();
    }

    function deleteDevRow(i) {
      devMgr.devices.splice(i, 1);
      if (devMgr.editingIdx >= devMgr.devices.length) devMgr.editingIdx = -1;
      renderDevMgr();
    }

    function addDevType() {
      const input = document.getElementById('devMgrNewType');
      const val = (input.value || '').trim();
      if (!val) return;
      if (devMgr.deviceTypes.some(t => t.toLowerCase() === val.toLowerCase())) return;
      devMgr.deviceTypes.push(val);
      input.value = '';
      renderDevMgr();
    }

    function deleteDevType(i) {
      devMgr.deviceTypes.splice(i, 1);
      renderDevMgr();
    }

    async function saveDevMgr() {
      // Commit any open edit row first
      if (devMgr.editingIdx !== -1) {
        const nameEl = document.getElementById('devMgrEditName');
        const typeEl = document.getElementById('devMgrEditType');
        const name = nameEl ? nameEl.value.trim() : '';
        const type = typeEl ? typeEl.value.trim() : '';
        const statusEl = document.getElementById('devMgrStatus');
        if (!name || !type) {
          if (statusEl) { statusEl.className = 'devmgr-status error'; statusEl.textContent = T('devMgrErrEmpty'); }
          return;
        }
        devMgr.devices[devMgr.editingIdx] = { name, type };
        devMgr.editingIdx = -1;
      }
      // Client-side validation
      const br = devMgr.backupRoot.trim();
      const statusEl = document.getElementById('devMgrStatus');
      const setErr = msg => { if (statusEl) { statusEl.className = 'devmgr-status error'; statusEl.textContent = msg; } };
      if (!br) { setErr('backupRoot is required'); return; }
      for (const d of devMgr.devices) {
        if (!d.name || !d.type) { setErr(T('devMgrErrEmpty')); return; }
      }
      const names = devMgr.devices.map(d => d.name.toLowerCase());
      if (new Set(names).size !== names.length) { setErr(T('devMgrErrDupe')); return; }

      if (statusEl) { statusEl.className = 'devmgr-status'; statusEl.textContent = T('devMgrSaving'); }
      try {
        const r1 = await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ backupRoot: br, devices: devMgr.devices, deviceTypes: devMgr.deviceTypes }),
        }).then(r => r.json());
        if (!r1.ok) { setErr(`Save failed: ${r1.error}`); return; }
      } catch (err) { setErr(`Save failed: ${err.message}`); return; }

      if (statusEl) { statusEl.className = 'devmgr-status'; statusEl.textContent = T('devMgrReloading'); }
      try {
        await fetch('/api/reload', { method: 'POST' });
        await loadFromServer();
        const n = state.parsedConfigs.length;
        if (statusEl) { statusEl.className = 'devmgr-status'; statusEl.textContent = T('devMgrDone', n); }
      } catch (err) { setErr(`Reload failed: ${err.message}`); }
    }
```

- [ ] **Step 2: Smoke-test in browser**
  - Open Import modal → click "Server Config" tab → panel loads with device list
  - Click Edit on a row → inline inputs appear
  - Save Row / Cancel work
  - ＋ Add Device appends a new editable row
  - Delete removes a row
  - Device Types chips render; × disabled when type is in use
  - Add new type via input → chip appears
  - Save & Reload → status cycles Saving… → Reloading… → Done. N device(s) loaded.

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat: add device manager JS (devMgr state + render + edit + save)"
```

---

### Task 7: `applyLang()` — wire tab label updates

**Files:**
- Modify: `public/index.html` — inside `applyLang()` function

- [ ] **Step 1: Add tab label updates to `applyLang()`**

In `applyLang()`, after the `sfEl` schedule filter block (the last block before `L('lblFilterSrc', ...)`), insert:

```js
      L('tabImport', 'tabImport');
      L('tabServerConfig', 'tabServerConfig');
      const devMgrPanel = document.getElementById('importTabServerConfig');
      if (devMgrPanel && !devMgrPanel.classList.contains('hidden')) renderDevMgr();
```

- [ ] **Step 2: Toggle language and verify tab labels switch correctly**

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat: wire device manager i18n in applyLang()"
```

---

### Task 8: Final commit and push

- [ ] **Step 1: Push all commits**

```bash
git push
```
