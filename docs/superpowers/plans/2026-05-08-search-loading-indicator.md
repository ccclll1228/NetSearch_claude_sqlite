# Search Loading Indicator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a CSS spinner + "Searching…" label on every search trigger in `public/index.html`, visible for at least one frame on synchronous tabs and for the full duration on async FQDN fetches.

**Architecture:** One static sibling `<div id="search-loading">` sits between `#tabBar` and `#content` in the HTML. Because it is never inside `#content`, it survives `el.innerHTML` replacement. `showLoading()` sets its display to `flex`; `hideLoading()` hides it via double `requestAnimationFrame` to guarantee one painted frame. Both are wired into `renderContent()` at the full-render branch (`!expandOnly`), covering every search trigger in one place.

**Tech Stack:** Vanilla JS, CSS custom properties (`--cds-*` tokens), existing `@keyframes spin` animation.

---

### Task 1: Add CSS

**Files:**
- Modify: `public/index.html` — CSS block near line 362

The existing `.search-spinner` block ends at line 378. `@keyframes spin` is declared at line 380. Add the new rules **between** `.search-spinner.active` and `@keyframes spin` so the existing animation is reused without redeclaration.

- [ ] **Step 1: Insert CSS rules after `.search-spinner.active { display: block; }` (line 378), before `@keyframes spin`**

Find this exact block:

```css
    .search-spinner.active {
      display: block;
    }

    @keyframes spin {
```

Replace with:

```css
    .search-spinner.active {
      display: block;
    }

    #search-loading {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      color: var(--cds-text-secondary);
      font-size: 12px;
      font-family: var(--cds-font-sans);
    }

    .loading-spinner {
      width: 14px;
      height: 14px;
      border: 2px solid var(--cds-border-subtle);
      border-top-color: var(--cds-interactive);
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      flex-shrink: 0;
    }

    @media (prefers-reduced-motion: reduce) {
      .loading-spinner { animation: none; opacity: 0.5; }
    }

    @keyframes spin {
```

- [ ] **Step 2: Verify no duplicate `@keyframes spin` declaration exists**

```bash
grep -n "@keyframes spin" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected: exactly **one** match.

---

### Task 2: Add HTML Element

**Files:**
- Modify: `public/index.html` — HTML near line 2637

- [ ] **Step 1: Insert `#search-loading` immediately before `<div class="content" id="content">`**

Find this exact line:

```html
    <div class="content" id="content"></div>
```

Replace with:

```html
    <div id="search-loading" style="display:none;" aria-live="polite">
      <span class="loading-spinner"></span>
      <span class="loading-text">Searching…</span>
    </div>
    <div class="content" id="content"></div>
```

- [ ] **Step 2: Verify the element exists in the DOM position**

```bash
grep -n "search-loading\|id=\"content\"" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html | head -10
```

Expected: `search-loading` div appears on a line number **immediately before** the `id="content"` line.

---

### Task 3: Add JS Helpers and Wire into `renderContent()`

**Files:**
- Modify: `public/index.html` — JS utility section (~line 2976) and `renderContent()` (~line 4534)

#### Step 3a — Add helpers in the utility section

- [ ] **Step 1: Insert `showLoading` and `hideLoading` after the `quickSearch` function, before `// ===== NETWORK UTILS =====`**

Find this exact line:

```js
    // ===== NETWORK UTILS =====
```

Insert immediately before it:

```js
    function showLoading() {
      document.getElementById('search-loading').style.display = 'flex';
    }
    function hideLoading() {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          document.getElementById('search-loading').style.display = 'none';
        });
      });
    }

    // ===== NETWORK UTILS =====
```

#### Step 3b — Wire into `renderContent()`

- [ ] **Step 2: Call `showLoading()` at the top of the full-render branch inside `renderContent()`**

Find this exact block (the `else` branch of the `expandOnly` check):

```js
      } else {
        _patchGeneration++; // cancel any in-flight rAF patch loops
        _groupTreeHtmlCache.clear();
        _pillContext.clear();
        d = renderTabs();
        _cachedFilterData = d;
        _filterCacheDirty = false;
      }
```

Replace with:

```js
      } else {
        showLoading();
        _patchGeneration++; // cancel any in-flight rAF patch loops
        _groupTreeHtmlCache.clear();
        _pillContext.clear();
        d = renderTabs();
        _cachedFilterData = d;
        _filterCacheDirty = false;
      }
```

- [ ] **Step 3: Call `hideLoading()` after the `el.innerHTML` switch statement**

Find this exact block:

```js
        default: el.innerHTML = '<div class="empty-state">Select a tab</div>';
      }
      updateFilterOptions();
```

Replace with:

```js
        default: el.innerHTML = '<div class="empty-state">Select a tab</div>';
      }
      hideLoading();
      updateFilterOptions();
```

- [ ] **Step 4: Verify wire-up with grep**

```bash
grep -n "showLoading\|hideLoading" /home/local/SSO/yt0115/NetSearch_sqlite/public/index.html
```

Expected output (4 matches total):
```
<line>:    function showLoading() {
<line>:    function hideLoading() {
<line>:        showLoading();
<line>:      hideLoading();
```

---

### Task 4: Verify and Commit

- [ ] **Step 1: Start the dev server**

```bash
cd /home/local/SSO/yt0115/NetSearch_sqlite && npm run dev
```

- [ ] **Step 2: Open the app and verify spinner appears on Enter key**

Navigate to `http://localhost:3002`. Type any search term and press Enter. Confirm the "Searching…" spinner flashes briefly above the results area before disappearing.

- [ ] **Step 3: Verify spinner appears on filter dropdown change**

Change any filter dropdown (e.g. FROM ZONE). Confirm spinner flashes.

- [ ] **Step 4: Verify spinner appears on FQDN tab**

Switch to the FQDN tab with a keyword active. Confirm spinner shows while records load, then disappears when the table renders.

- [ ] **Step 5: Verify pill expand/collapse does NOT show spinner**

Expand a pill on Sec Rules. Confirm no spinner appears.

- [ ] **Step 6: Commit**

```bash
git add public/index.html
git commit -m "feat: add search loading indicator with double-rAF hide"
```

---

## Self-Review

**Spec coverage:**
- ✅ DOM element as sibling between `#tabBar` and `#content` — Task 2
- ✅ CSS with `--cds-*` tokens, reuses existing `@keyframes spin` — Task 1
- ✅ `prefers-reduced-motion` — Task 1 Step 1
- ✅ `showLoading()` / `hideLoading()` helpers with double-rAF — Task 3a
- ✅ Wire-up in `renderContent()` full-render branch only — Task 3b
- ✅ `expandOnly` path excluded — Task 3b (only `else` branch gets `showLoading()`)
- ✅ `#searchSpinner` untouched — no task touches it
- ✅ `renderFqdnDb` loading text untouched — no task touches it

**Placeholder scan:** No TBDs, no vague steps, all code blocks are complete.

**Type consistency:** `showLoading` / `hideLoading` named consistently across all three task steps that reference them.
