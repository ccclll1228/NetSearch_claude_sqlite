# Device List Manager Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Device Manager panel inside the existing Import modal (as a second tab) that lets users view, add, edit, and delete server-configured devices and persist changes to `config/settings.json` without SSH access.

**Architecture:** Two new API endpoints (`GET/POST /api/settings`) on the server; a tab switcher added to the import modal with a self-contained `devMgr` local state object; no changes to global `state` or any other tab.

**Tech Stack:** Vanilla JS (inline in `public/index.html`), Express (`server.js`), `fs.readFileSync`/`fs.writeFileSync` for settings persistence.

---

## Section 1 — Backend (`server.js`)

### `GET /api/settings`

Reads `settings.json` synchronously and returns a safe subset:

```json
{ "backupRoot": "...", "devices": [...], "deviceTypes": [...] }
```

If `deviceTypes` is absent from the file, the response defaults it to `["paloalto", "f5", "fortigate", "srx"]`. No other keys (`port`, `cronSchedule`, etc.) are returned — they are not editable in this UI.

### `POST /api/settings`

Accepts `{ backupRoot, devices, deviceTypes }`.

**Server-side validation** (returns `{ ok: false, error: "..." }` on failure):
- `backupRoot`: non-empty string after trim
- `devices`: array; each entry has non-empty `name` (trimmed) and non-empty `type` (trimmed)
- No duplicate device names (case-insensitive)
- `deviceTypes`: array of ≥ 1 non-empty strings

On success: reads current `settings.json`, merges in the three new fields (preserving `port`, `cronSchedule`, and any other existing keys), writes back with `fs.writeFileSync`, returns `{ ok: true }`.

Single-user internal tool — no concurrent-write guard needed.

### No changes to `POST /api/reload`

After a successful save the frontend calls `/api/reload` exactly as the header Reload button does.

---

## Section 2 — Modal Tab Structure

The import modal (`#importModal`) gets a two-tab bar inserted immediately after `<div class="modal-body">`:

```html
<div class="devmgr-tabs" id="importTabBar">
  <button class="devmgr-tab active" id="tabImport"
          onclick="switchImportTab('import')">Import</button>
  <button class="devmgr-tab" id="tabServerConfig"
          onclick="switchImportTab('serverConfig')">Server Config</button>
</div>
<div id="importTabImport">  <!-- existing modal body content -->
<div id="importTabServerConfig" class="hidden">  <!-- new panel -->
```

`switchImportTab(name)` toggles the `active` class on the tab buttons and `hidden` on the two panels. When switching to `serverConfig` for the first time (or after a successful save+reload), it calls `loadDevMgr()`.

**Tab CSS** — new rule, using `--cds-*` tokens:

```css
.devmgr-tabs { display:flex; border-bottom:1px solid var(--cds-border-subtle); margin-bottom:12px; }
.devmgr-tab  { flex:none; padding:6px 16px; font-size:12px; font-family:var(--cds-font-sans);
               background:none; border:none; border-bottom:2px solid transparent;
               cursor:pointer; color:var(--cds-text-secondary); }
.devmgr-tab.active { color:var(--cds-text-primary); border-bottom-color:var(--cds-interactive); font-weight:600; }
.devmgr-tab:hover:not(.active) { background:var(--cds-layer-hover); }
```

---

## Section 3 — Server Config Panel Layout

```
Backup Root Directory
[/home/oxidized/backups                                        ]

Devices                                          [＋ Add Device]
┌──────────────────────────┬────────────┬──────────────────────┐
│ Name                     │ Type       │ Actions              │
├──────────────────────────┼────────────┼──────────────────────┤
│ FRI-FW01                 │ paloalto   │ [Edit]  [Delete]     │
│ FRI-LTM01                │ f5         │ [Edit]  [Delete]     │
└──────────────────────────┴────────────┴──────────────────────┘

Device Types
[paloalto ×]  [f5 ×]  [fortigate ×]  [srx ×]
[____________] [Add]

[Save & Reload]   <status text here>
```

### Inline row editing

Clicking **Edit** on a row sets `devMgr.editingIdx` to that row's index and re-renders. The row becomes:

```
[FRI-FW01 (input)]  [paloalto ▾ (select)]  [Save Row]  [Cancel]
```

The `<select>` is populated from `devMgr.deviceTypes`. Clicking **Save Row** trims values, validates (non-empty name, no duplicate among other rows), commits to `devMgr.devices[idx]`, and sets `editingIdx = -1`. **Cancel** restores the previous value without saving. Only one row can be in edit mode at a time.

### New Device row

**＋ Add Device** appends `{ name: '', type: devMgr.deviceTypes[0] }` to `devMgr.devices` and sets `editingIdx` to the new row's index. Saving or cancelling follows the same inline-edit flow.

### Device Types chips

Each chip shows the type label and a `×` delete button. Deleting a type that is currently assigned to one or more devices is prevented — the `×` button is disabled (greyed) with a tooltip `"In use"`. The add-type input is a plain text input; pressing Enter or clicking **Add** trims the value, checks for duplicates (case-insensitive), and appends to `devMgr.deviceTypes`.

### Save & Reload button

Located at the bottom of the panel. On click:
1. Runs client-side validation (same rules as server). If invalid, shows error in status div and aborts.
2. Sets status to `"Saving…"` (i18n key `devMgrSaving`).
3. `POST /api/settings` — on error shows `"Save failed: <msg>"` in red.
4. On success: sets status to `"Reloading…"` (`devMgrReloading`).
5. `POST /api/reload` — on success: sets status to `"Done. N devices loaded."` (`devMgrDone`), calls `renderContent()`.
6. On any error in step 5: shows `"Reload failed: <msg>"` in red.

---

## Section 4 — `devMgr` State Object

```js
const devMgr = {
  backupRoot: '',
  devices: [],        // [{ name, type }]  — working copy
  deviceTypes: [],    // ['paloalto', 'f5', ...]  — working copy
  editingIdx: -1,     // index of row currently in edit mode; -1 = none
};
```

`loadDevMgr()` fetches `GET /api/settings` and populates `devMgr`. All edits (add/delete row, inline save, type chip delete, add type) mutate `devMgr` directly and call `renderDevMgr()` to re-render the panel. No changes touch global `state` until `POST /api/reload` returns and `renderContent()` is called.

`renderDevMgr()` renders only `#importTabServerConfig` — it never touches `#importTabImport` or calls `getFilteredData()`.

---

## Section 5 — i18n

New keys added to both `en` and `zh` objects:

| Key | en | zh |
|-----|----|----|
| `tabImport` | `'Import'` | `'匯入'` |
| `tabServerConfig` | `'Server Config'` | `'伺服器設定'` |
| `devMgrBackupRoot` | `'Backup Root Directory'` | `'備份根目錄'` |
| `devMgrDevices` | `'Devices'` | `'設備列表'` |
| `devMgrAddDevice` | `'＋ Add Device'` | `'＋ 新增設備'` |
| `devMgrDeviceTypes` | `'Device Types'` | `'設備類型'` |
| `devMgrAddType` | `'Add'` | `'新增'` |
| `devMgrEdit` | `'Edit'` | `'編輯'` |
| `devMgrDelete` | `'Delete'` | `'刪除'` |
| `devMgrSaveRow` | `'Save'` | `'儲存'` |
| `devMgrCancel` | `'Cancel'` | `'取消'` |
| `devMgrSaveReload` | `'Save & Reload'` | `'儲存並重載'` |
| `devMgrSaving` | `'Saving…'` | `'儲存中…'` |
| `devMgrReloading` | `'Reloading…'` | `'重載中…'` |
| `devMgrDone` | `'Done. {0} devices loaded.'` | `'完成。已載入 {0} 台設備。'` |
| `devMgrInUse` | `'In use'` | `'使用中'` |

`applyLang()` updates the two static tab button labels (`#tabImport`, `#tabServerConfig`) and re-renders `renderDevMgr()` if the Server Config tab is currently visible.

---

## Section 6 — `config/settings.example.json`

Add `"deviceTypes"` field:

```json
{
  "port": 3000,
  "backupRoot": "/home/oxidized/backups",
  "devices": [ ... ],
  "deviceTypes": ["paloalto", "f5", "fortigate", "srx"],
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

---

## Section 7 — Files Changed

| File | Change |
|------|--------|
| `server.js` | Add `GET /api/settings` and `POST /api/settings` routes |
| `public/index.html` | Tab bar HTML, Server Config panel HTML, `devMgr` state + functions, CSS, i18n keys, `applyLang()` update |
| `config/settings.example.json` | Add `"deviceTypes"` field |

`lib/parser.js`, `lib/fqdn_db.js`, `lib/discovery.js`, `lib/scheduler.js`, and all other files are **not touched**.
