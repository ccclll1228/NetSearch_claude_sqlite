# Zone Pills Static Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace expandable pill rendering for FROM/TO zone columns in Sec Rules and NAT Rules with plain static `.pill` spans that have no toggle, search, or copy buttons.

**Architecture:** Add a single `renderZonePills(list)` function immediately after `renderPills` in `public/index.html`, then update the 4 call sites (2 in `renderSecRules`, 2 in `renderNatRules`) to use it. No other files are touched.

**Tech Stack:** Vanilla JS, inline HTML template literals, existing `.pill` CSS class.

---

### Task 1: Add `renderZonePills` function

**Files:**
- Modify: `public/index.html:4886-4887`

- [ ] **Step 1: Insert the function after the closing brace of `renderPills` (line 4886)**

The block from line 4879 currently ends at line 4887 (blank line after `}`). Insert the new function in that gap so it reads:

```js
    function renderPills(list, parsed, type = 'object', ctx = '') {
      if (!list || list.length === 0) return '<span class="text-muted text-sm">—</span>';
      return '<div class="pills">' + list.map(item => {
        const pid = ctx ? `${item}_${parsed?.hostname || ''}_${ctx}` : `${item}_${parsed?.hostname || ''}`;
        _pillContext.set(pid, { item, type, parsed, ctx }); // store for targeted DOM updates
        return renderOnePill(item, type, parsed, ctx, pid);
      }).join('') + '</div>';
    }

    function renderZonePills(list) {
      if (!list || list.length === 0) return '<span class="text-muted text-sm">—</span>';
      return '<div class="pills">' + list.map(z => `<span class="pill">${esc(z)}</span>`).join('') + '</div>';
    }
```

Use the Edit tool. `old_string` = the closing `}` + blank line of `renderPills`:

```
    }


    function togglePill(pid) {
```

`new_string`:

```
    }

    function renderZonePills(list) {
      if (!list || list.length === 0) return '<span class="text-muted text-sm">—</span>';
      return '<div class="pills">' + list.map(z => `<span class="pill">${esc(z)}</span>`).join('') + '</div>';
    }

    function togglePill(pid) {
```

- [ ] **Step 2: Verify the function is present**

Run:
```bash
grep -n "renderZonePills" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected output — exactly 1 definition line, 0 call sites yet:
```
4888:    function renderZonePills(list) {
```

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat: add renderZonePills static zone pill renderer"
```

---

### Task 2: Update FROM/TO call sites in `renderSecRules`

**Files:**
- Modify: `public/index.html:5121`

Line 5121 is a single long template-literal string containing both FROM and TO `renderPills` calls in the same div:

```js
        <div class="rule-field"><div style="display:flex;align-items:baseline;gap:5px;margin-bottom:3px"><span class="rule-field-label" style="margin:0;flex-shrink:0;min-width:24px">FROM</span>${renderPills(r.from, r._parsed, 'object', ruleKey)}</div><div style="display:flex;align-items:baseline;gap:5px"><span class="rule-field-label" style="margin:0;flex-shrink:0;min-width:24px">TO</span>${renderPills(r.to, r._parsed, 'object', ruleKey)}</div></div>
```

- [ ] **Step 1: Replace both renderPills calls on line 5121**

`old_string`:
```
        <div class="rule-field"><div style="display:flex;align-items:baseline;gap:5px;margin-bottom:3px"><span class="rule-field-label" style="margin:0;flex-shrink:0;min-width:24px">FROM</span>${renderPills(r.from, r._parsed, 'object', ruleKey)}</div><div style="display:flex;align-items:baseline;gap:5px"><span class="rule-field-label" style="margin:0;flex-shrink:0;min-width:24px">TO</span>${renderPills(r.to, r._parsed, 'object', ruleKey)}</div></div>
```

`new_string`:
```
        <div class="rule-field"><div style="display:flex;align-items:baseline;gap:5px;margin-bottom:3px"><span class="rule-field-label" style="margin:0;flex-shrink:0;min-width:24px">FROM</span>${renderZonePills(r.from)}</div><div style="display:flex;align-items:baseline;gap:5px"><span class="rule-field-label" style="margin:0;flex-shrink:0;min-width:24px">TO</span>${renderZonePills(r.to)}</div></div>
```

- [ ] **Step 2: Verify the change**

```bash
grep -n "renderPills(r\.from\|renderPills(r\.to\|renderZonePills" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected — secRules line now uses `renderZonePills`, natRules lines still use `renderPills`:
```
4888:    function renderZonePills(list) {
5121:        <div class="rule-field">..FROM..${renderZonePills(r.from)}..TO..${renderZonePills(r.to)}..
5198:            `<div class="rule-field">...${renderPills(r.from, r._parsed, 'object', ruleKey)}</div>`,
5199:            `<div class="rule-field">...${renderPills(r.to, r._parsed, 'object', ruleKey)}</div>`,
```

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat: use renderZonePills for FROM/TO in renderSecRules"
```

---

### Task 3: Update FROM/TO call sites in `renderNatRules`

**Files:**
- Modify: `public/index.html:5198-5199`

Lines 5198–5199 are two separate array element strings inside `const cells = [...]`:

```js
            `<div class="rule-field"><div class="rule-field-label">${T('natFrom')}</div>${renderPills(r.from, r._parsed, 'object', ruleKey)}</div>`,
            `<div class="rule-field"><div class="rule-field-label">${T('natTo')}</div>${renderPills(r.to, r._parsed, 'object', ruleKey)}</div>`,
```

- [ ] **Step 1: Replace both renderPills calls on lines 5198–5199**

`old_string`:
```
            `<div class="rule-field"><div class="rule-field-label">${T('natFrom')}</div>${renderPills(r.from, r._parsed, 'object', ruleKey)}</div>`,
            `<div class="rule-field"><div class="rule-field-label">${T('natTo')}</div>${renderPills(r.to, r._parsed, 'object', ruleKey)}</div>`,
```

`new_string`:
```
            `<div class="rule-field"><div class="rule-field-label">${T('natFrom')}</div>${renderZonePills(r.from)}</div>`,
            `<div class="rule-field"><div class="rule-field-label">${T('natTo')}</div>${renderZonePills(r.to)}</div>`,
```

- [ ] **Step 2: Verify no `renderPills(r.from` or `renderPills(r.to` remain**

```bash
grep -n "renderPills(r\.from\|renderPills(r\.to" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: no output (zero matches).

- [ ] **Step 3: Verify renderZonePills appears exactly 3 times (1 definition + 4 call sites = but grep for definition + calls)**

```bash
grep -c "renderZonePills" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: `5` (1 definition + 4 call sites: 2 in secRules, 2 in natRules).

- [ ] **Step 4: Commit**

```bash
git add public/index.html
git commit -m "feat: use renderZonePills for FROM/TO in renderNatRules"
```
