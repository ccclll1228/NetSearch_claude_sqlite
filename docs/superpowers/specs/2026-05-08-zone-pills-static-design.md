# Zone Pills Static Rendering — Design Spec

## Goal

In the Sec Rules and NAT Rules expanded row UI, render FROM and TO zone values as plain, non-interactive `.pill` spans instead of expandable/collapsible pill cards. All other columns (SOURCE, DESTINATION, SERVICE, APPLICATION, TRANSLATION) are unchanged.

## Background

`renderPills(list, parsed, type, ctx)` is the shared renderer for all rule cell values. It calls `renderOnePill`, which produces expandable containers with toggle arrows, QS buttons, and copy buttons. This is appropriate for address objects and services (which resolve to members), but zones are simple string identifiers (`trust`, `untrust`, `dmz`) — they have no group members to expand into and gain nothing from the interactive chrome.

## Approach

**Option A — dedicated `renderZonePills(list)` function.** A new, self-contained function that emits static `.pill` spans. `renderPills` and `renderOnePill` are untouched.

## Design

### New function

```js
function renderZonePills(list) {
  if (!list || list.length === 0) return '<span class="text-muted text-sm">—</span>';
  return '<div class="pills">' + list.map(z => `<span class="pill">${esc(z)}</span>`).join('') + '</div>';
}
```

- No `_pillContext` registration
- No `expandable` class, no `onclick`, no `data-ppid`
- No QS or copy buttons
- Empty list falls back to the standard `—` muted dash, matching all other cells
- Reuses `.pill` CSS class unchanged — same background, border, font as today

### Call-site changes (4 total, all in `public/index.html`)

**`renderSecRules`** — line ~5121, the FROM/TO combined `rule-field` div:

Before:
```js
renderPills(r.from, r._parsed, 'object', ruleKey)
// ...
renderPills(r.to, r._parsed, 'object', ruleKey)
```

After:
```js
renderZonePills(r.from)
// ...
renderZonePills(r.to)
```

**`renderNatRules`** — lines ~5198–5199, FROM and TO cell strings:

Before:
```js
renderPills(r.from, r._parsed, 'object', ruleKey)
renderPills(r.to,   r._parsed, 'object', ruleKey)
```

After:
```js
renderZonePills(r.from)
renderZonePills(r.to)
```

### What is NOT changed

- `renderPills`, `renderOnePill`, `togglePill` — untouched
- SOURCE, DESTINATION, SERVICE, APPLICATION, TRANSLATION cells — untouched
- `expandableItems` arrays in both renderers — left as-is; expand/collapse all buttons will simply find no matching DOM nodes for zone items, which is harmless
- All filtering, search, and highlight logic — untouched
- CSS — no new classes or rules needed

## Files

- Modify: `public/index.html` — add `renderZonePills` near `renderPills`; update 4 call sites
