# Filter Bar Checkbox → Dropdown Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three checkbox groups in the global filter bar with three `<select class="filter-select">` dropdowns, keeping all filter logic identical.

**Architecture:** Single file edit in `public/index.html`. Four localized touch-points: the `#filterBar` HTML block, the `addEventListener` init block, `clearAllFilters()`, and `applyLang()`. All state variables and filter logic are untouched — only the control type changes from checkbox to select.

**Tech Stack:** Vanilla JS, HTML, CSS (`filter-select` class already defined).

---

### Task 1: Replace checkboxes with dropdowns in `public/index.html`

**Files:**
- Modify: `public/index.html:2651–2661` (filter bar HTML)
- Modify: `public/index.html:6330–6331` (applyLang)
- Modify: `public/index.html:6353–6357` (addEventListener init block)
- Modify: `public/index.html:6458–6462` (clearAllFilters)

> There are no automated tests for this project. Verification is manual in the browser.

---

- [ ] **Step 1: Replace the filter bar HTML**

Open `public/index.html`. Find lines 2651–2661. The current content is:

```html
      <label class="filter-toggle"><input type="checkbox" id="filterSource" /> <span
          id="lblFilterSrc">Src</span></label>
      <label class="filter-toggle"><input type="checkbox" id="filterDest" /> <span id="lblFilterDst">Dst</span></label>
      <span style="width:1px;height:16px;background:var(--border);margin:0 2px"></span>
      <label class="filter-toggle"><input type="checkbox" id="secHideDisabled" /> <span id="lblHideDisabled">Hide
          Disabled</span></label>
      <label class="filter-toggle"><input type="checkbox" id="secShowDisabledOnly" /> <span
          id="lblDisabledOnly">Disabled Only</span></label>
      <span style="width:1px;height:16px;background:var(--border);margin:0 2px"></span>
      <label class="filter-toggle"><input type="checkbox" id="showDisabledMembersOnly" /> <span id="lblF5Disabled">F5
          Disabled</span></label>
```

Replace the entire block above with:

```html
      <select class="filter-select" id="ipFilter"
        onchange="const v=this.value;state.filters.filterSource=v==='src';state.filters.filterDest=v==='dst';renderContent()">
        <option value="">IP (All)</option>
        <option value="src">Src</option>
        <option value="dst">Dst</option>
      </select>
      <select class="filter-select" id="ruleDisabledFilter"
        onchange="const v=this.value;state.filters.secHideDisabled=v==='hide';state.filters.natHideDisabled=v==='hide';state.filters.secShowDisabledOnly=v==='only';state.filters.natShowDisabledOnly=v==='only';renderContent()">
        <option value="">RULE (All)</option>
        <option value="hide">Hide Disabled</option>
        <option value="only">Disabled Only</option>
      </select>
      <select class="filter-select" id="f5DisabledFilter"
        onchange="state.filters.showDisabledMembersOnly=this.value==='only';renderContent()">
        <option value="">F5 (All)</option>
        <option value="only">Disabled Only</option>
      </select>
```

---

- [ ] **Step 2: Remove the 5 old `addEventListener` calls**

Find lines 6353–6357 (immediately after the `tagFilter` listener). The current content is:

```js
    document.getElementById('filterSource').addEventListener('change', e => { state.filters.filterSource = e.target.checked; renderContent(); });
    document.getElementById('filterDest').addEventListener('change', e => { state.filters.filterDest = e.target.checked; renderContent(); });
    document.getElementById('secHideDisabled').addEventListener('change', e => { state.filters.secHideDisabled = e.target.checked; state.filters.natHideDisabled = e.target.checked; if (e.target.checked) { state.filters.secShowDisabledOnly = false; state.filters.natShowDisabledOnly = false; } document.getElementById('secShowDisabledOnly').checked = false; renderContent(); });
    document.getElementById('secShowDisabledOnly').addEventListener('change', e => { state.filters.secShowDisabledOnly = e.target.checked; state.filters.natShowDisabledOnly = e.target.checked; if (e.target.checked) { state.filters.secHideDisabled = false; state.filters.natHideDisabled = false; } document.getElementById('secHideDisabled').checked = false; renderContent(); });
    document.getElementById('showDisabledMembersOnly').addEventListener('change', e => { state.filters.showDisabledMembersOnly = e.target.checked; renderContent(); });
```

Delete all 5 lines. The new selects use inline `onchange`; no replacement listeners are needed.

---

- [ ] **Step 3: Update `clearAllFilters()` to reset the new selects**

Find lines 6458–6462 inside `clearAllFilters()`. The current content is:

```js
      document.getElementById('filterSource').checked = false;
      document.getElementById('filterDest').checked = false;
      document.getElementById('secHideDisabled').checked = false;
      document.getElementById('secShowDisabledOnly').checked = false;
      document.getElementById('showDisabledMembersOnly').checked = false;
```

Replace with:

```js
      document.getElementById('ipFilter').value = '';
      document.getElementById('ruleDisabledFilter').value = '';
      document.getElementById('f5DisabledFilter').value = '';
```

---

- [ ] **Step 4: Remove the 5 stale `L()` calls from `applyLang()`**

Find lines 6330–6331. The current content is:

```js
      L('lblFilterSrc', 'filterSrc'); L('lblFilterDst', 'filterDst');
      L('lblHideDisabled', 'hideDisabled'); L('lblDisabledOnly', 'disabledOnly'); L('lblF5Disabled', 'f5Disabled');
```

Delete both lines. The span IDs they target no longer exist. The new `<option>` text is static English — consistent with all other `<select>` elements on the page (SCHEDULE, FROM ZONE, TO ZONE).

---

- [ ] **Step 5: Start the server and verify in the browser**

```bash
npm start
```

Open `http://localhost:3002` and check:

1. The filter bar shows three dropdowns: **IP (All)**, **RULE (All)**, **F5 (All)** — no checkboxes between SCHEDULE and the Expand button.
2. Select **IP → Src**: rules update to show only source-matching results. Select **(All)**: full results return.
3. Select **IP → Dst**: rules update to destination-only results. Select **(All)**: full results return.
4. Select **RULE → Hide Disabled**: disabled rules are hidden. Select **Disabled Only**: only disabled rules show. Select **(All)**: all rules show.
5. Select **F5 → Disabled Only** (with F5 device loaded): only disabled F5 pool members show. Select **(All)**: all show.
6. Click **✕ Clear**: all three dropdowns reset to **(All)** and results return to unfiltered state.
7. Toggle language to 中文 (if applicable) and confirm no JS console errors.

---

- [ ] **Step 6: Commit**

```bash
git add public/index.html
git commit -m "feat: replace filter bar checkboxes with dropdown selects"
```
