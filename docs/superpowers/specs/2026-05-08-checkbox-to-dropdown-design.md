# Filter Bar Checkbox → Dropdown Replacement

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the three checkbox groups in the global filter bar with three `<select>` dropdowns, matching the existing Carbon-style `filter-select` pattern. No filter logic changes — only the HTML control type and its wiring change.

---

## Scope

Single file: `public/index.html`. Four touch-points within that file:

| Location | What changes |
|---|---|
| `#filterBar` HTML (~line 2651) | Remove 5 `<label class="filter-toggle">` + 2 separator `<span>`; add 3 `<select class="filter-select">` |
| `addEventListener` init block (~line 6353) | Remove 5 checkbox listeners |
| `clearAllFilters()` (~line 6458) | Replace 5 `.checked = false` with 3 `.value = ''` |
| `applyLang()` (~line 6330) | Remove 5 `L()` calls whose target span IDs no longer exist |

No changes to `getFilteredData()`, `renderSecRules()`, `renderNatRules()`, `renderF5Virtuals()`, `renderF5Pools()`, or any other function.

---

## New Dropdowns

### IP dropdown — `id="ipFilter"`

Replaces `filterSource` (Src) + `filterDest` (Dst) checkboxes.

```html
<select class="filter-select" id="ipFilter"
  onchange="const v=this.value;state.filters.filterSource=v==='src';state.filters.filterDest=v==='dst';renderContent()">
  <option value="">IP (All)</option>
  <option value="src">Src</option>
  <option value="dst">Dst</option>
</select>
```

State mapping:

| Option value | `filterSource` | `filterDest` |
|---|---|---|
| `""` (All) | `false` | `false` |
| `"src"` | `true` | `false` |
| `"dst"` | `false` | `true` |

### Rule dropdown — `id="ruleDisabledFilter"`

Replaces `secHideDisabled` (Hide Disabled) + `secShowDisabledOnly` (Disabled Only) checkboxes.

```html
<select class="filter-select" id="ruleDisabledFilter"
  onchange="const v=this.value;state.filters.secHideDisabled=v==='hide';state.filters.natHideDisabled=v==='hide';state.filters.secShowDisabledOnly=v==='only';state.filters.natShowDisabledOnly=v==='only';renderContent()">
  <option value="">RULE (All)</option>
  <option value="hide">Hide Disabled</option>
  <option value="only">Disabled Only</option>
</select>
```

State mapping:

| Option value | `secHideDisabled` | `natHideDisabled` | `secShowDisabledOnly` | `natShowDisabledOnly` |
|---|---|---|---|---|
| `""` (All) | `false` | `false` | `false` | `false` |
| `"hide"` | `true` | `true` | `false` | `false` |
| `"only"` | `false` | `false` | `true` | `true` |

### F5 dropdown — `id="f5DisabledFilter"`

Replaces `showDisabledMembersOnly` checkbox. Two options only (no "Hide Disabled" — no existing state for it).

```html
<select class="filter-select" id="f5DisabledFilter"
  onchange="state.filters.showDisabledMembersOnly=this.value==='only';renderContent()">
  <option value="">F5 (All)</option>
  <option value="only">Disabled Only</option>
</select>
```

State mapping:

| Option value | `showDisabledMembersOnly` |
|---|---|
| `""` (All) | `false` |
| `"only"` | `true` |

---

## Removals

### From `#filterBar` HTML

Remove exactly these 7 elements (5 labels + 2 separators):

```html
<label class="filter-toggle"><input type="checkbox" id="filterSource" /> <span id="lblFilterSrc">Src</span></label>
<label class="filter-toggle"><input type="checkbox" id="filterDest" /> <span id="lblFilterDst">Dst</span></label>
<span style="width:1px;height:16px;background:var(--border);margin:0 2px"></span>
<label class="filter-toggle"><input type="checkbox" id="secHideDisabled" /> <span id="lblHideDisabled">Hide Disabled</span></label>
<label class="filter-toggle"><input type="checkbox" id="secShowDisabledOnly" /> <span id="lblDisabledOnly">Disabled Only</span></label>
<span style="width:1px;height:16px;background:var(--border);margin:0 2px"></span>
<label class="filter-toggle"><input type="checkbox" id="showDisabledMembersOnly" /> <span id="lblF5Disabled">F5 Disabled</span></label>
```

### From event listener init block

Remove these 5 `addEventListener` calls:

```js
document.getElementById('filterSource').addEventListener(...)
document.getElementById('filterDest').addEventListener(...)
document.getElementById('secHideDisabled').addEventListener(...)
document.getElementById('secShowDisabledOnly').addEventListener(...)
document.getElementById('showDisabledMembersOnly').addEventListener(...)
```

### From `clearAllFilters()`

Remove:
```js
document.getElementById('filterSource').checked = false;
document.getElementById('filterDest').checked = false;
document.getElementById('secHideDisabled').checked = false;
document.getElementById('secShowDisabledOnly').checked = false;
document.getElementById('showDisabledMembersOnly').checked = false;
```

Add:
```js
document.getElementById('ipFilter').value = '';
document.getElementById('ruleDisabledFilter').value = '';
document.getElementById('f5DisabledFilter').value = '';
```

### From `applyLang()`

Remove these 2 lines (the span IDs they target no longer exist):
```js
L('lblFilterSrc', 'filterSrc'); L('lblFilterDst', 'filterDst');
L('lblHideDisabled', 'hideDisabled'); L('lblDisabledOnly', 'disabledOnly'); L('lblF5Disabled', 'f5Disabled');
```

The new option text is static English — consistent with all other `<select>` elements in the page (including SCHEDULE, FROM ZONE, TO ZONE).

---

## Unchanged

- All state variables: `filterSource`, `filterDest`, `secHideDisabled`, `natHideDisabled`, `secShowDisabledOnly`, `natShowDisabledOnly`, `showDisabledMembersOnly`
- All filter logic in `getFilteredData()`, `renderSecRules()`, `renderNatRules()`, `renderF5Virtuals()`, `renderF5Pools()`
- Visual style: `<select class="filter-select">` matches all existing dropdowns
- Position: the three new selects occupy the same position in the filter bar as the controls they replace
