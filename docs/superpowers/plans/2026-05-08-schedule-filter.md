# Schedule Filter for Sec Rules — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Schedule dropdown to the global filter bar that filters Sec Rules to show all rules, scheduled-only, or unscheduled-only.

**Architecture:** Four targeted edits to `public/index.html`: (1) add `scheduleFilter` to `state.filters` and `clearAllFilters()`; (2) add i18n keys and wire `applyLang()` to update option texts; (3) insert the static HTML dropdown after the TAG select; (4) add `hasAppliedSchedule()` utility and two guard lines in the sec rules loop.

**Tech Stack:** Vanilla JS, inline HTML, existing `state.filters` pattern.

---

### Task 1: State — add `scheduleFilter` key

**Files:**
- Modify: `public/index.html:2798` (state.filters object)
- Modify: `public/index.html:6390` (clearAllFilters function)

- [ ] **Step 1: Add `scheduleFilter: ''` to `state.filters`**

Find this exact line (around line 2798):

```js
        fromZone: '', toZone: '', tag: '',
```

Replace with:

```js
        fromZone: '', toZone: '', tag: '', scheduleFilter: '',
```

- [ ] **Step 2: Add `scheduleFilter` to `clearAllFilters()`**

Find this exact line (around line 6390):

```js
      state.filters = { sourceDevice: '', fromZone: '', toZone: '', tag: '', filterSource: false, filterDest: false, secHideDisabled: false, secShowDisabledOnly: false, natHideDisabled: false, natShowDisabledOnly: false, showDisabledMembersOnly: false, fqdnTypeFilter: '', fqdnOwnerFilter: '', fqdnGeoFilter: '' };
```

Replace with:

```js
      state.filters = { sourceDevice: '', fromZone: '', toZone: '', tag: '', scheduleFilter: '', filterSource: false, filterDest: false, secHideDisabled: false, secShowDisabledOnly: false, natHideDisabled: false, natShowDisabledOnly: false, showDisabledMembersOnly: false, fqdnTypeFilter: '', fqdnOwnerFilter: '', fqdnGeoFilter: '' };
```

- [ ] **Step 3: Reset the DOM select in `clearAllFilters()`**

Find this block (immediately after the state reset line):

```js
      document.getElementById('fromZoneFilter').value = '';
      document.getElementById('toZoneFilter').value = '';
      document.getElementById('tagFilter').value = '';
```

Replace with:

```js
      document.getElementById('fromZoneFilter').value = '';
      document.getElementById('toZoneFilter').value = '';
      document.getElementById('tagFilter').value = '';
      document.getElementById('scheduleFilter').value = '';
```

- [ ] **Step 4: Verify**

```bash
grep -n "scheduleFilter" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: exactly 3 matches (state.filters declaration, clearAllFilters reset, DOM reset).

---

### Task 2: i18n — add translation keys and wire `applyLang()`

**Files:**
- Modify: `public/index.html:2839` (`en` translation object)
- Modify: `public/index.html:2919` (`zh` translation object)
- Modify: `public/index.html:6268` (`applyLang()` function)

- [ ] **Step 1: Add keys to the `en` translation object**

Find this exact line (around line 2839):

```js
        fromZoneAll: 'FROM ZONE (All)', toZoneAll: 'TO ZONE (All)', tagAll: 'TAG (All)',
```

Replace with:

```js
        fromZoneAll: 'FROM ZONE (All)', toZoneAll: 'TO ZONE (All)', tagAll: 'TAG (All)', scheduleAll: 'SCHEDULE (All)', scheduleOnly: 'Scheduled Only', scheduleNone: 'Unscheduled Only',
```

- [ ] **Step 2: Add keys to the `zh` translation object**

Find this exact line (around line 2919):

```js
        fromZoneAll: 'FROM ZONE（全部）', toZoneAll: 'TO ZONE（全部）', tagAll: 'TAG（全部）',
```

Replace with:

```js
        fromZoneAll: 'FROM ZONE（全部）', toZoneAll: 'TO ZONE（全部）', tagAll: 'TAG（全部）', scheduleAll: '排程（全部）', scheduleOnly: '僅排程', scheduleNone: '僅無排程',
```

- [ ] **Step 3: Wire `applyLang()` to update the dropdown option texts**

Find this exact line in `applyLang()` (around line 6268):

```js
      L('lblFilterSrc', 'filterSrc'); L('lblFilterDst', 'filterDst');
```

Insert immediately before it:

```js
      const sfEl = document.getElementById('scheduleFilter');
      if (sfEl) { sfEl.options[0].text = T('scheduleAll'); sfEl.options[1].text = T('scheduleOnly'); sfEl.options[2].text = T('scheduleNone'); }
```

- [ ] **Step 4: Verify i18n keys exist in both objects**

```bash
grep -n "scheduleAll\|scheduleOnly\|scheduleNone" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: 6 matches (2 per key across `en` and `zh`), plus the `applyLang` update block (3 more references) = 9 total.

---

### Task 3: HTML — insert dropdown in filter bar

**Files:**
- Modify: `public/index.html:2624` (filter bar HTML)

- [ ] **Step 1: Insert `#scheduleFilter` select after the TAG select**

Find this exact block (around line 2624):

```html
      <select class="filter-select" id="tagFilter">
        <option value="">TAG (All)</option>
      </select>
      <label class="filter-toggle"><input type="checkbox" id="filterSource" />
```

Replace with:

```html
      <select class="filter-select" id="tagFilter">
        <option value="">TAG (All)</option>
      </select>
      <select class="filter-select" id="scheduleFilter"
        onchange="state.filters.scheduleFilter=this.value;renderContent()">
        <option value="">SCHEDULE (All)</option>
        <option value="scheduled">Scheduled Only</option>
        <option value="unscheduled">Unscheduled Only</option>
      </select>
      <label class="filter-toggle"><input type="checkbox" id="filterSource" />
```

- [ ] **Step 2: Verify placement**

```bash
grep -n "scheduleFilter\|tagFilter\|filterSource" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html | head -10
```

Expected: `tagFilter` select appears before `scheduleFilter` select, which appears before `filterSource` label, all in sequential line numbers.

---

### Task 4: JS — utility function and filter pipeline

**Files:**
- Modify: `public/index.html:2976` (utility section — near `clearSearch`/`quickSearch`)
- Modify: `public/index.html:4047` (sec rules loop in `getFilteredData()`)

- [ ] **Step 1: Add `hasAppliedSchedule` utility function**

Find this exact line (around line 2976 — the `// ===== NETWORK UTILS =====` line, which is now preceded by `showLoading`/`hideLoading`):

```js
    function showLoading() {
```

Insert immediately before it:

```js
    function hasAppliedSchedule(rule) {
      const v = String(rule.schedule || '').trim().toLowerCase();
      return !!v && v !== 'none' && v !== 'any' && v !== 'always';
    }

```

- [ ] **Step 2: Add guard lines in the sec rules loop**

Find this exact block (around line 4047 — inside the sec rules loop in `getFilteredData()`):

```js
          if (filters.fromZone && !r.from.includes(filters.fromZone)) return;
          if (filters.toZone && !r.to.includes(filters.toZone)) return;
          if (filters.tag && !(r.tag || []).includes(filters.tag)) return;
          let match = true;
```

Replace with:

```js
          if (filters.fromZone && !r.from.includes(filters.fromZone)) return;
          if (filters.toZone && !r.to.includes(filters.toZone)) return;
          if (filters.tag && !(r.tag || []).includes(filters.tag)) return;
          if (filters.scheduleFilter === 'scheduled'   && !hasAppliedSchedule(r)) return;
          if (filters.scheduleFilter === 'unscheduled' &&  hasAppliedSchedule(r)) return;
          let match = true;
```

- [ ] **Step 3: Verify `hasAppliedSchedule` and guard lines**

```bash
grep -n "hasAppliedSchedule\|scheduleFilter" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected output includes:
- `function hasAppliedSchedule` — definition
- Two `hasAppliedSchedule(r)` — in guard lines
- `scheduleFilter` — in state, clearAllFilters, HTML onchange, and the two guard lines

Also confirm the NAT rules loop (around line 4095–4097) does NOT contain `scheduleFilter`:

```bash
sed -n '4090,4100p' /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: only `fromZone`, `toZone`, `tag` guards — no `scheduleFilter`.

---

### Task 5: Verify and commit

- [ ] **Step 1: Full grep check — confirm all 4 changes landed**

```bash
grep -c "scheduleFilter" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: 9 or more matches (state init, clearAllFilters state reset, clearAllFilters DOM reset, HTML onchange, applyLang options[0/1/2] references, two guard lines).

- [ ] **Step 2: Confirm `_isAlways` is untouched**

```bash
grep -n "_isAlways" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: same 4 lines as before (definition + 3 usages inside `renderSecRules`), all within the 5009–5040 line range.

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat: add Schedule filter for Sec Rules"
```

---

## Self-Review

**Spec coverage:**
- ✅ `scheduleFilter: ''` in `state.filters` — Task 1 Step 1
- ✅ Reset in `clearAllFilters()` (state + DOM) — Task 1 Steps 2–3
- ✅ i18n keys in `en` and `zh` — Task 2 Steps 1–2
- ✅ `applyLang()` updates option texts — Task 2 Step 3
- ✅ HTML dropdown after TAG select — Task 3 Step 1
- ✅ `hasAppliedSchedule(rule)` utility — Task 4 Step 1
- ✅ Two guard lines after `filters.tag` in sec rules loop — Task 4 Step 2
- ✅ NAT rules loop untouched — Task 4 Step 3 verification
- ✅ `_isAlways` untouched — Task 5 Step 2 verification

**Placeholder scan:** No TBDs, all code blocks complete.

**Type consistency:** `scheduleFilter` key named identically across all five tasks. `hasAppliedSchedule` named identically in Task 4 Steps 1 and 2. Option values `'scheduled'`/`'unscheduled'` match between HTML (Task 3) and guard lines (Task 4).
