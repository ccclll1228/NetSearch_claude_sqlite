# Schedule Filter for Sec Rules — Design Spec

**Date:** 2026-05-08
**File:** `public/index.html`
**Status:** Approved

---

## Problem

There is no way to filter Sec Rules by whether a schedule is applied. Users who want to see only time-restricted rules (or only always-active rules) must scan manually.

---

## Goal

Add a `Schedule` dropdown to the global filter bar. Selecting "Scheduled Only" keeps rules that have a real schedule applied; "Unscheduled Only" keeps rules with no meaningful schedule. The filter applies only to the Sec Rules pipeline and is always visible in the filter bar regardless of the active tab, consistent with the existing FROM ZONE / TO ZONE / TAG pattern.

---

## Scope

- `public/index.html` only.
- Sec Rules filtering pipeline only — NAT Rules, FQDN, Routes, Objects, LTM, Pools, and Copy tabs are unaffected.
- No backend changes.
- The existing `_isAlways` helper inside `renderSecRules()` is not touched.

---

## Design

### 1. State

One new key added to `state.filters`, initialised to empty string:

```js
scheduleFilter: '',   // '' = All | 'scheduled' = Scheduled Only | 'unscheduled' = Unscheduled Only
```

### 2. HTML Dropdown

Inserted in the static filter bar HTML (`id="filterBar"`) immediately after the TAG `<select>`, before the Src/Dst checkboxes:

```html
<select class="filter-select" id="scheduleFilter"
  onchange="state.filters.scheduleFilter=this.value;renderContent()">
  <option value="">SCHEDULE (All)</option>
  <option value="scheduled">Scheduled Only</option>
  <option value="unscheduled">Unscheduled Only</option>
</select>
```

The dropdown is always visible regardless of active tab. It has no effect on any tab other than Sec Rules.

### 3. i18n

Three translation keys added to both `en` and `zh` objects. `applyLang()` sets the option texts, following the same pattern as `fromZoneAll` / `toZoneAll` / `tagAll`:

| Key | `en` | `zh` |
|---|---|---|
| `scheduleAll` | `SCHEDULE (All)` | `排程（全部）` |
| `scheduleOnly` | `Scheduled Only` | `僅排程` |
| `scheduleNone` | `Unscheduled Only` | `僅無排程` |

`applyLang()` sets the option texts using these keys on the `#scheduleFilter` select element.

### 4. Utility Function

Added in the JS utility section alongside `clearSearch` / `quickSearch`:

```js
function hasAppliedSchedule(rule) {
  const v = String(rule.schedule || '').trim().toLowerCase();
  return !!v && v !== 'none' && v !== 'any' && v !== 'always';
}
```

`rule.schedule` may be `null`, a raw string (e.g. `'always'`, `'Business-Hours'`), or a resolved schedule object (e.g. `{ name, start, end }`). `String(...)` normalises all three cases: `null` → `''`, string → as-is, object → `'[object Object]'` which is truthy and not any of the excluded values — meaning any resolved schedule object is treated as a real schedule.

### 5. Filter Pipeline

Two guard lines added to the Sec Rules loop inside `getFilteredData()`, immediately after the existing `filters.tag` check:

```js
if (filters.fromZone && !r.from.includes(filters.fromZone)) return;
if (filters.toZone  && !r.to.includes(filters.toZone))   return;
if (filters.tag     && !(r.tag || []).includes(filters.tag)) return;
if (filters.scheduleFilter === 'scheduled'   && !hasAppliedSchedule(r)) return;
if (filters.scheduleFilter === 'unscheduled' &&  hasAppliedSchedule(r)) return;
```

These lines run before the keyword search block, consistent with all other guard filters. The NAT Rules loop is not modified.

---

## Behaviour Summary

| `scheduleFilter` value | Effect |
|---|---|
| `''` (default) | No filtering — all rules pass |
| `'scheduled'` | Keep only rules where `hasAppliedSchedule(r)` is `true` |
| `'unscheduled'` | Keep only rules where `hasAppliedSchedule(r)` is `false` |

Combining with other active filters (keyword search, FROM ZONE, TO ZONE, TAG, Hide Disabled, Disabled Only) works via the existing AND-chain — each guard is independent.

---

## Not In Scope

- Hiding or greying out the dropdown on non-Sec-Rules tabs.
- Filtering NAT Rules, FQDN, or any other tab.
- Any backend or server-side changes.
- Changes to `_isAlways` or the schedule column rendering in `renderSecRules()`.
