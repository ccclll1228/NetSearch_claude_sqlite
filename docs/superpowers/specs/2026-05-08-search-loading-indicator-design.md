# Search Loading Indicator — Design Spec

**Date:** 2026-05-08
**File:** `public/index.html`
**Status:** Approved

---

## Problem

There is no visual feedback when a search is triggered. On fast synchronous tabs (Sec Rules, NAT, Routes, Objects, F5) the results appear instantly, but users get no confirmation that their input was received. On the FQDN tab during async fetches, the only feedback is a plain-text "Loading FQDN records…" string with no animation.

---

## Goal

Show a spinner + "Searching…" label on every search trigger — synchronous tabs included — and hide it once results are written to the DOM. Users always see at least one visible frame of feedback regardless of render speed.

---

## Scope

- `public/index.html` only — one file, three additions (HTML, CSS, JS).
- No changes to search logic, filter behavior, result rendering, or any other file.
- The existing `#searchSpinner` in the header bar is left untouched.

---

## Design

### 1. DOM Element

Insert one static element between `#tabBar` and `#content` in the HTML:

```html
<div id="search-loading" style="display:none;" aria-live="polite">
  <span class="loading-spinner"></span>
  <span class="loading-text">Searching…</span>
</div>
<div class="content" id="content"></div>
```

**Why a sibling, not a child of `#content`:** `renderContent()` replaces `#content.innerHTML` on every full render. A child element would be destroyed before it could be seen. As a sibling, it is never touched by render calls and survives both sync and async render cycles.

### 2. CSS

Added alongside the existing `.search-spinner` block. Reuses the existing `@keyframes spin` — no duplicate declaration.

```css
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
```

All color and font values use `--cds-*` tokens, consistent with the rest of the UI.

### 3. JS Helpers

Two functions added to the JS utilities section:

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
```

**Double `requestAnimationFrame` contract:** The browser must paint at least one frame between show and hide. A single rAF schedules the hide callback before the next paint; a double rAF schedules it one paint *after* that, guaranteeing the spinner is visible for at least one rendered frame on even the fastest synchronous renders.

### 4. Wire-up

`showLoading()` is called at the top of the full-render path inside `renderContent()`, and `hideLoading()` is called after the `el.innerHTML = ...` switch statement:

```js
function renderContent(expandOnly = false) {
  if (!expandOnly) showLoading();   // ← added
  // ... existing filter/render logic ...
  const el = document.getElementById('content');
  switch (state.activeTab) {
    case 'sec':      el.innerHTML = renderSecRules(d.secRules);        break;
    case 'nat':      el.innerHTML = renderNatRules(d.natRules);        break;
    // ... other cases ...
  }
  hideLoading();                    // ← added (double-rAF, non-blocking)
}
```

**Why hook inside `renderContent()` rather than at every call site:** There are 20+ call sites (Enter key, filter dropdowns, tab switch, search mode toggle, sort buttons, etc.). Hooking once inside `renderContent()` covers them all without touching each one. `expandOnly=true` calls (pill expand/collapse, device group toggle, copy tab field changes) are excluded — those are not search triggers.

**FQDN async path:** `fqdnDbAutoLoad()` calls `renderContent()` twice — once at fetch start (to show the "Loading FQDN records…" state) and once on completion (to show results). The spinner fires naturally at both moments with no additional wiring. The existing plain-text loading state in `renderFqdnDb()` is preserved as-is.

---

## Behavior Summary

| Trigger | `showLoading()` fires | `hideLoading()` fires |
|---|---|---|
| Enter key (any tab) | Top of `renderContent()` full path | After `el.innerHTML = ...` + 2 rAF |
| Filter dropdown change | Top of `renderContent()` full path | After `el.innerHTML = ...` + 2 rAF |
| Tab switch | Top of `renderContent()` full path | After `el.innerHTML = ...` + 2 rAF |
| Search mode toggle | Top of `renderContent()` full path | After `el.innerHTML = ...` + 2 rAF |
| FQDN async fetch start | Top of `renderContent()` full path | After `el.innerHTML = ...` + 2 rAF |
| FQDN async fetch complete | Top of `renderContent()` full path | After `el.innerHTML = ...` + 2 rAF |
| Pill expand/collapse (`expandOnly=true`) | Not called | Not called |
| Device group toggle (`expandOnly=true`) | Not called | Not called |
| Server reload (`loadFromServer`) | Not called (uses `#searchSpinner`) | Not called |

---

## Not In Scope

- Changes to `#searchSpinner` (header bar spinner shown on Enter key and server reload).
- Changes to the "Loading FQDN records…" text in `renderFqdnDb()`.
- Any changes outside `public/index.html`.
