# Combined Copy Engine Strengthen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 12 identified gaps between the Combined Copy engine spec and current implementation in `NetSearch-prototype.html`.

**Architecture:** All changes are contained within `NetSearch-prototype.html` — a single-file app. The Combined Copy logic lives in `generateCopyData()` (line ~2173), `renderCopyTab()` (line ~2101), `COPY_FIELDS` (line ~2070), and `copyTSV()` (line ~2348). Changes follow the existing pattern: vanilla JS globals, no framework.

**Tech Stack:** Vanilla JS, single HTML file, no build step, no external dependencies.

---

## File Map

| Location | What Changes |
|---|---|
| `NetSearch-prototype.html:2070–2097` | `COPY_FIELDS` — add 7 missing fields |
| `NetSearch-prototype.html:2098` | Add `lastGeneratedFilters` state variable |
| `NetSearch-prototype.html:2101–2165` | `renderCopyTab` — dirty hint + button disabled logic |
| `NetSearch-prototype.html:2173–2346` | `generateCopyData` — doNamesMatch, FQDN-led, field fixes |
| `NetSearch-prototype.html:2348–2357` | `copyTSV` — Excel-safe multi-value formatting |

---

## Gap Summary (12 issues)

| # | Gap | Severity |
|---|---|---|
| 1 | `doNamesMatch` missing — NAT matching uses exact string, spec says prefix/similarity | High |
| 2 | FQDN-led matching missing — should anchor on FQDN when data exists | High |
| 3 | `fqdn_type`, `fqdn_owner`, `fqdn_geo` not populated in matched rows | High |
| 4 | `nat_name` key not set in NAT entries/rows (stored as `rule_name` only) | High |
| 5 | `f5_pool`/`f5_members` confusion in row assignment | High |
| 6 | 7 COPY_FIELDS missing: URL Category, NAT Zone (from/to), NAT Orig Src/Dst, F5 Port, F5 Status | Medium |
| 7 | TSV multi-value: strips newlines, should use `\n`+quotes for Excel; UI preview should use `/` | Medium |
| 8 | Dirty hint only tracks `appliedSearch`, not zone/tag filter changes | Medium |
| 9 | "Generate Preview" button always enabled — should disable when no filters set | Medium |
| 10 | `copyDisplayLimit` resets to 200 after generation, should reset to 50 | Low |
| 11 | `f5_dest` is combined `ip:port`; spec requires separate `Dest IP` and `Port` fields | Low |
| 12 | `nat_zone` (from/to) and `nat_orig_src`/`nat_orig_dst` not extracted from NAT entries | Medium |

---

### Task 1: Add `doNamesMatch` utility function

**Files:**
- Modify: `NetSearch-prototype.html` (insert before `generateCopyData`, around line 2173)

This replaces the current exact-name NAT matching (`n.rule_name===sec.rule_name`) with prefix/similarity logic as described in the spec ("常用底線 `_` 分割名稱來比對").

- [ ] **Step 1: Locate insertion point**

Find line 2173: `function generateCopyData() {`
Insert the new helper function just before it.

- [ ] **Step 2: Add `doNamesMatch` function**

```javascript
// Helper: check if two rule names belong to the same business request
// Matches by first two underscore-separated segments (case-insensitive)
function doNamesMatch(name1, name2) {
  if (!name1 || !name2) return false;
  if (name1 === name2) return true;
  const seg1 = name1.split('_');
  const seg2 = name2.split('_');
  // At least the first segment must match
  if (seg1[0].toLowerCase() !== seg2[0].toLowerCase()) return false;
  // If both have a second segment, it must also match
  if (seg1.length > 1 && seg2.length > 1) {
    return seg1[1].toLowerCase() === seg2[1].toLowerCase();
  }
  return true;
}
```

- [ ] **Step 3: Update NAT matching in `generateCopyData` (line ~2279)**

Replace:
```javascript
const matchedNat=allNatEntries.find(n=>n.rule_name===sec.rule_name && n.hostname===sec.hostname);
```
With:
```javascript
const matchedNat=allNatEntries.find(n=>doNamesMatch(n.nat_name||n.rule_name, sec.rule_name) && n.hostname===sec.hostname);
```

- [ ] **Step 4: Fix the standalone NAT dedup guard (line ~2313)**

The current guard compares against sec `rule_name`s exactly, which breaks after `doNamesMatch` is introduced. Replace the `usedNatNames` dedup approach with a Set tracking which NAT entries were *actually* consumed during `buildSecRow`:

```javascript
// Declare this Set before the sec-rule loop (or FQDN-led loop), then populate
// it inside buildSecRow when a NAT match is found:
const usedNatKeys = new Set();
```

Inside `buildSecRow`, after `if(matchedNat){`, add:
```javascript
usedNatKeys.add(`${matchedNat.hostname}|${matchedNat.nat_name||matchedNat.rule_name}`);
```

Then in the standalone NAT loop, replace the current guard:
```javascript
// OLD (exact name match — broken after doNamesMatch):
// const usedNatNames=new Set(allSecEntries.map(s=>`${s.hostname}|${s.rule_name}`));
// if(usedNatNames.has(`${nat.hostname}|${nat.rule_name}`)) return;

// NEW (tracks actually-consumed NAT entries):
if(usedNatKeys.has(`${nat.hostname}|${nat.nat_name||nat.rule_name}`)) return;
```

- [ ] **Step 5: Manual test — load config with NAT rules whose names share a prefix (e.g., `APP_WEB_sec` and `APP_WEB_nat`). Verify they are merged into one row and the NAT rule does NOT also appear as a duplicate standalone row.**

---

### Task 2: Fix missing FQDN row fields

**Files:**
- Modify: `NetSearch-prototype.html:2296–2308` (FQDN match block inside `generateCopyData`)

Currently when a FQDN match is found, only `fqdn`, `domain`, `ip` are set. The spec lists `DNS Type`, `Owner`, `GeoInfo` as optional but selectable fields.

- [ ] **Step 1: Locate the FQDN match assignment block (line ~2302)**

```javascript
row.fqdn=fRec.fqdn; row.domain=fRec.domain; row.ip=fRec.ip;
```

- [ ] **Step 2: Extend assignment to include all FQDN fields**

Replace the single assignment line with:
```javascript
row.fqdn=fRec.fqdn;
row.domain=fRec.domain;
row.ip=fRec.ip;
row.fqdn_type=fRec.type||fRec.fqdn_type||'';
row.fqdn_owner=fRec.owner||fRec.fqdn_owner||'';
row.fqdn_geo=fRec.geoInfo||fRec.geo||fRec.fqdn_geo||'';  // parser stores as geoInfo (capital I)
```

- [ ] **Step 3: Verified — `parseFqdnFile` stores geo as `geoInfo` (capital I, line ~1253). The fallback chain above reflects this.**

---

### Task 3: Fix `nat_name` key in NAT entries and rows

**Files:**
- Modify: `NetSearch-prototype.html:2243–2257` (allNatEntries build loop)
- Modify: `NetSearch-prototype.html:2312–2320` (standalone NAT row push)

Currently `allNatEntries` stores the NAT rule name only as `rule_name`. COPY_FIELDS has key `nat_name`. They never connect.

- [ ] **Step 1: Add `nat_name` to allNatEntries push (line ~2246)**

In `allNatEntries.push({...})`, add:
```javascript
nat_name: r.name,
```
alongside the existing `rule_name: r.name`.

- [ ] **Step 2: Fix standalone NAT row to set `nat_name` (line ~2316)**

In the standalone NAT rows.push:
```javascript
rows.push({hostname:nat.hostname, rule_name:nat.rule_name, nat_name:nat.nat_name||nat.rule_name, action:'NAT',
  from:nat.from, to:nat.to, source:nat.source, destination:nat.destination,
  service:nat.service, application:'', fqdn:'', domain:'', ip:'',
  nat_snat:nat.nat_snat, nat_dnat:nat.nat_dnat, f5_vs:'', f5_pool:'', f5_members:''});
```

- [ ] **Step 3: Fix main sec+NAT row (line ~2276) to also set `nat_name`**

In the initial `row={}` construction, add `nat_name:''`. After matched NAT, add `row.nat_name=matchedNat.nat_name||matchedNat.rule_name`.

---

### Task 4: Fix `f5_pool` / `f5_members` assignment bug

**Files:**
- Modify: `NetSearch-prototype.html:2292` (F5 match in sec rule loop)
- Modify: `NetSearch-prototype.html:2327–2330` (standalone F5 row)

The current code sets `f5_pool = matchedF5.f5_members || matchedF5.f5_pool`, which conflates the pool *name* with the pool *members* list.

- [ ] **Step 1: Fix the F5 match assignment in the sec rule loop (line ~2292)**

Replace:
```javascript
if(matchedF5){row.f5_vs=matchedF5.f5_vs;row.f5_pool=matchedF5.f5_members||matchedF5.f5_pool;}
```
With:
```javascript
if(matchedF5){
  row.f5_vs=matchedF5.f5_vs;
  row.f5_pool=matchedF5.f5_pool;
  row.f5_members=matchedF5.f5_members;
  row.f5_dest=matchedF5.f5_ip;
  row.f5_port=matchedF5.f5_port;
  row.f5_status=matchedF5.f5_status||'';
}
```

- [ ] **Step 2: Fix the standalone F5 row push (line ~2327)**

Replace:
```javascript
rows.push({hostname:f.hostname, rule_name:f.f5_vs, action:'LB',
  from:'', to:'', source:'any', destination:f.f5_dest,
  service:'', application:'', fqdn:'', domain:'', ip:'',
  nat_snat:'', nat_dnat:'', f5_vs:f.f5_vs, f5_pool:f.f5_members||f.f5_pool});
```
With:
```javascript
rows.push({hostname:f.hostname, rule_name:f.f5_vs, nat_name:'', action:'LB',
  from:'', to:'', source:'any', destination:f.f5_dest,
  service:'', application:'', fqdn:'', domain:'', ip:'',
  fqdn_type:'', fqdn_owner:'', fqdn_geo:'',
  nat_snat:'', nat_dnat:'',
  f5_vs:f.f5_vs, f5_dest:f.f5_ip, f5_port:f.f5_port, f5_pool:f.f5_pool,
  f5_members:f.f5_members, f5_status:f.f5_status||''});
```

- [ ] **Step 3: Fix allF5Entries push to include `f5_ip`, `f5_port`, `f5_status` separately (line ~2262)**

In `allF5Entries.push({...})`:
```javascript
allF5Entries.push({
  hostname:vs._hostname, f5_vs:vs.name,
  f5_dest:`${vs.ip}:${vs.port}`,   // keep combined for backward compat display
  f5_ip:vs.ip,
  f5_port:String(vs.port||''),
  f5_status:vs.status||'enabled',  // parser already writes 'disabled'|'enabled' to vs.status
  f5_pool:vs.pool||'',
  f5_members:pool?(pool.members||[]).map(m=>`${m.ip}:${m.port}`).join('; '):'',
  _type:'f5'
});
```

---

### Task 5: Add 7 missing COPY_FIELDS entries

**Files:**
- Modify: `NetSearch-prototype.html:2078–2097` (COPY_FIELDS definition)

Spec requires: URL Category (Sec Rules), NAT Zone from/to, NAT Original Src/Dst, F5 Port, F5 Status.

- [ ] **Step 1: Add `url_category` to Security Rules group (after `application` at line 2087)**

```javascript
{key:'url_category',label:'URL Category',group:'Security Rules',selected:false},
```

- [ ] **Step 2: Add NAT Zone and Original Src/Dst fields (after existing `nat_name` at line 2089)**

```javascript
{key:'nat_name',label:'NAT Rule Name',group:'NAT Rules',selected:true},
{key:'nat_from',label:'NAT Zone From',group:'NAT Rules',selected:false},
{key:'nat_to',label:'NAT Zone To',group:'NAT Rules',selected:false},
{key:'nat_orig_src',label:'Original Src',group:'NAT Rules',selected:false},
{key:'nat_orig_dst',label:'Original Dst',group:'NAT Rules',selected:false},
{key:'nat_snat',label:'SNAT',group:'NAT Rules',selected:false},
{key:'nat_dnat',label:'DNAT',group:'NAT Rules',selected:false},
```

- [ ] **Step 3: Add F5 Port and Status fields (after `f5_dest` at line 2094)**

```javascript
{key:'f5_vs',label:'VS Name',group:'LTM',selected:true},
{key:'f5_dest',label:'VS Dest IP',group:'LTM',selected:true},
{key:'f5_port',label:'VS Port',group:'LTM',selected:false},
{key:'f5_status',label:'VS Status',group:'LTM',selected:false},
{key:'f5_pool',label:'Pool Name',group:'LTM',selected:true},
{key:'f5_members',label:'Pool Members',group:'LTM',selected:true},
```

- [ ] **Step 4: Populate new fields in `generateCopyData` — NAT entries**

In `allNatEntries.push({...})`, add:
```javascript
nat_from:(r.from||[]).join(', '),
nat_to:(r.to||[]).join(', '),
nat_orig_src:expandObjList(r.source,p.addresses,p.groups).join(', '),
nat_orig_dst:expandObjList(r.destination,p.addresses,p.groups).join(', '),
```

- [ ] **Step 5: Populate `url_category` in `allSecEntries`**

In `allSecEntries.push({...})`, add:
```javascript
url_category:(r.category||[]).join(', '),  // PA/FG parsers store URL category as r.category
```

- [ ] **Step 6: Propagate `nat_from`, `nat_to`, `nat_orig_src`, `nat_orig_dst` into sec+NAT matched rows**

After `row.nat_snat=matchedNat.nat_snat; row.nat_dnat=matchedNat.nat_dnat;`, add:
```javascript
row.nat_from=matchedNat.nat_from||'';
row.nat_to=matchedNat.nat_to||'';
row.nat_orig_src=matchedNat.nat_orig_src||'';
row.nat_orig_dst=matchedNat.nat_orig_dst||'';
```

- [ ] **Step 7: Initialize all new fields to empty string in the initial `row={}` construction in the sec loop**

---

### Task 6: Implement FQDN-led matching

**Files:**
- Modify: `NetSearch-prototype.html:2271–2310` (Phase 2 correlation logic)

Spec: "先遍歷 FQDN 列表，查找有相同 IP 的 Sec/NAT 規則與 LTM VS". When FQDN data is present, FQDN should be the outer loop key.

- [ ] **Step 1: Wrap the current sec-rule loop in a FQDN-branch**

Replace the current loop structure with a conditional:

```javascript
// Decide iteration strategy
if (d.fqdnList && d.fqdnList.length > 0) {
  // FQDN-led: one row per (FQDN × matching sec rule)
  d.fqdnList.forEach(fRec => {
    if (!fRec.ip || fRec.ip === 'null') return;

    // Find all sec rules whose src/dst IPs match this FQDN IP
    const matchingSecEntries = allSecEntries.filter(sec => {
      for (const rip of [...sec._srcIps, ...sec._dstIps]) {
        if (matchFqdnToIp(rip, fRec)) return true;
      }
      return false;
    });

    if (matchingSecEntries.length === 0) {
      // FQDN with no matching rule — emit FQDN-only row
      rows.push(buildFqdnOnlyRow(fRec));
      return;
    }

    matchingSecEntries.forEach(sec => {
      const row = buildSecRow(sec);
      // Attach FQDN
      row.fqdn=fRec.fqdn; row.domain=fRec.domain; row.ip=fRec.ip;
      row.fqdn_type=fRec.type||fRec.fqdn_type||'';
      row.fqdn_owner=fRec.owner||fRec.fqdn_owner||'';
      row.fqdn_geo=fRec.geoInfo||fRec.geo||fRec.fqdn_geo||'';
      rows.push(row);
    });
  });
} else {
  // Sec-rule-led: original behavior (no FQDN data loaded)
  allSecEntries.forEach(sec => {
    const row = buildSecRow(sec);
    rows.push(row);
  });
}
```

- [ ] **Step 2: Extract `buildSecRow(sec)` helper inside `generateCopyData`**

This helper creates a row from a sec entry, performs NAT/F5 matching, and returns the row. Extract the existing sec loop body (~line 2272–2310) into this inner function to avoid duplication.

```javascript
const buildSecRow = (sec) => {
  const row={
    hostname:sec.hostname, rule_name:sec.rule_name, nat_name:'', action:sec.action,
    from:sec.from, to:sec.to, source:sec.source, destination:sec.destination,
    service:sec.service, application:sec.application, url_category:sec.url_category||'',
    fqdn:'', domain:'', ip:'', fqdn_type:'', fqdn_owner:'', fqdn_geo:'',
    nat_from:'', nat_to:'', nat_orig_src:'', nat_orig_dst:'',
    nat_snat:'', nat_dnat:'',
    f5_vs:'', f5_dest:'', f5_port:'', f5_status:'', f5_pool:'', f5_members:''
  };
  // NAT match
  const matchedNat = allNatEntries.find(n =>
    doNamesMatch(n.nat_name||n.rule_name, sec.rule_name) && n.hostname===sec.hostname
  );
  if (matchedNat) {
    row.nat_name=matchedNat.nat_name||matchedNat.rule_name;
    row.nat_snat=matchedNat.nat_snat; row.nat_dnat=matchedNat.nat_dnat;
    row.nat_from=matchedNat.nat_from||''; row.nat_to=matchedNat.nat_to||'';
    row.nat_orig_src=matchedNat.nat_orig_src||''; row.nat_orig_dst=matchedNat.nat_orig_dst||'';
    // F5 match via NAT DNAT IP
    if (matchedNat._dnatIps.size > 0) {
      const matchedF5 = allF5Entries.find(f => {
        for (const dip of matchedNat._dnatIps) {
          if (isExactIP(String(dip)) && f.f5_ip===String(dip)) return true;
          if (isCIDR(String(dip)) && ipInCIDR(f.f5_ip, String(dip))) return true;
        }
        return false;
      });
      if (matchedF5) {
        row.f5_vs=matchedF5.f5_vs; row.f5_dest=matchedF5.f5_ip;
        row.f5_port=matchedF5.f5_port; row.f5_status=matchedF5.f5_status||'';
        row.f5_pool=matchedF5.f5_pool; row.f5_members=matchedF5.f5_members;
      }
    }
  }
  return row;
};
```

- [ ] **Step 3: Extract `buildFqdnOnlyRow(fRec)` helper**

```javascript
const buildFqdnOnlyRow = (fRec) => ({
  hostname:'', rule_name:'', nat_name:'', action:'',
  from:'', to:'', source:'', destination:'', service:'', application:'', url_category:'',
  fqdn:fRec.fqdn, domain:fRec.domain, ip:fRec.ip,
  fqdn_type:fRec.type||fRec.fqdn_type||'',
  fqdn_owner:fRec.owner||fRec.fqdn_owner||'',
  fqdn_geo:fRec.geoInfo||fRec.geo||fRec.fqdn_geo||'',
  nat_from:'', nat_to:'', nat_orig_src:'', nat_orig_dst:'',
  nat_snat:'', nat_dnat:'',
  f5_vs:'', f5_dest:'', f5_port:'', f5_status:'', f5_pool:'', f5_members:''
});
```

- [ ] **Step 4: Test — load FQDN data + firewall config. Verify rows now anchor on FQDN IPs.**

---

### Task 7: Fix TSV multi-value Excel formatting

**Files:**
- Modify: `NetSearch-prototype.html:2348–2357` (`copyTSV` function)
- Modify: `NetSearch-prototype.html:2156` (preview table cell rendering)

Spec: Copy output should use `\n` + double-quote wrapping for multi-value cells (Excel standard). UI preview should use `/` separator.

- [ ] **Step 1: Define which keys are "array/multiline" fields**

Add a Set constant near `COPY_FIELDS`:
```javascript
const MULTILINE_KEYS = new Set([
  'source','destination','service','application','url_category',
  'nat_orig_src','nat_orig_dst','nat_snat','nat_dnat',
  'f5_members'
]);
```

- [ ] **Step 2: Rewrite `copyTSV` to use Excel multi-line format for those fields**

```javascript
function copyTSV() {
  if(copyData.length===0)return;
  const selFields=copyFields.filter(f=>f.selected);
  const header=selFields.map(f=>f.label).join('\t');
  const body=copyData.map(row=>
    selFields.map(f=>{
      const val=String(row[f.key]||'');
      if(MULTILINE_KEYS.has(f.key) && val.includes(', ')){
        // Excel multi-line cell: replace separators with \n and wrap in quotes
        const lines=val.split(', ').join('\n');
        return `"${lines.replace(/"/g,'""')}"`;
      }
      return val.replace(/[\t]/g,' ');
    }).join('\t')
  ).join('\n');
  const tsv=header+'\n'+body;
  navigator.clipboard.writeText(tsv).then(()=>{showCopyFeedback();}).catch(()=>{
    const ta=document.createElement('textarea');ta.value=tsv;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showCopyFeedback();
  });
}
```

- [ ] **Step 3: Update preview table cell rendering (line ~2156) to use `/` for multi-value fields**

Change the preview `<td>` rendering from `esc(row[f.key]||'')` to:
```javascript
const previewVal = (key, val) => {
  if (MULTILINE_KEYS.has(key) && val && val.includes(', ')) {
    return val.split(', ').join(' / ');
  }
  return val;
};
```
And use `esc(previewVal(f.key, row[f.key]||''))` in the table cell.

---

### Task 8: Fix dirty hint to track filter changes

**Files:**
- Modify: `NetSearch-prototype.html:526` (`state` definition — add `lastGeneratedFilters`)
- Modify: `NetSearch-prototype.html:2102` (`renderCopyTab` dirty check)
- Modify: `NetSearch-prototype.html:2343` (`generateCopyData` state save)

- [ ] **Step 1: Add `lastGeneratedFilters` to state (line ~526, OUTSIDE the `filters:{}` block)**

`state` has two relevant areas: `lastGeneratedSearch:''` at line 526, and the nested `filters:{}` object at lines 527–535. Insert as a **top-level sibling** of `lastGeneratedSearch`, not inside `filters:{}`:

```javascript
lastGeneratedSearch: '',
lastGeneratedFilters: {fromZone:'', toZone:'', tag:''},  // ← top-level, NOT inside filters:{}
filters: {
  ...
```

- [ ] **Step 2: Update dirty check in `renderCopyTab` (line ~2102)**

Replace:
```javascript
const isDirty = copyData.length>0 && state.lastGeneratedSearch !== state.appliedSearch;
```
With:
```javascript
const isDirty = copyData.length > 0 && (
  state.lastGeneratedSearch !== state.appliedSearch ||
  state.lastGeneratedFilters.fromZone !== state.filters.fromZone ||
  state.lastGeneratedFilters.toZone !== state.filters.toZone ||
  state.lastGeneratedFilters.tag !== state.filters.tag
);
```

- [ ] **Step 3: Save filter snapshot in `generateCopyData` (line ~2343)**

After `state.lastGeneratedSearch=state.appliedSearch;`, add:
```javascript
state.lastGeneratedFilters = {
  fromZone: state.filters.fromZone,
  toZone: state.filters.toZone,
  tag: state.filters.tag
};
```

---

### Task 9: Disable "Generate Preview" when no filters set

**Files:**
- Modify: `NetSearch-prototype.html:2146` (Generate Preview button in `renderCopyTab`)

- [ ] **Step 1: Add `hasAnyFilter` computation in `renderCopyTab` (before the preview panel HTML)**

```javascript
const hasAnyFilter = !!(state.appliedSearch ||
  state.filters.fromZone || state.filters.toZone || state.filters.tag);
```

- [ ] **Step 2: Disable the button and add tooltip when no filter**

Change:
```html
<button class="btn btn-primary btn-sm" onclick="generateCopyData()">Generate Preview</button>
```
To:
```javascript
`<button class="btn btn-primary btn-sm" onclick="generateCopyData()" ${!hasAnyFilter?'disabled title="Enter a search term or select a filter first"':''}>Generate Preview</button>`
```

- [ ] **Step 3: Replace the old `if(!state.appliedSearch)` guard in `renderCopyTab` (line ~2151) with `if(!hasAnyFilter)`**

The old guard only handles the missing-search case. Replace:
```javascript
if(!state.appliedSearch){
  previewHtml+=`<div class="empty-state" style="padding:30px">Please enter a search term first.</div>`;
```
With:
```javascript
if(!hasAnyFilter){
  previewHtml+=`<div class="empty-state" style="padding:30px">Enter a search term or select a zone/tag filter to enable preview generation.</div>`;
```

- [ ] **Step 4: Update the `generateCopyData` entry guard (line ~2174) to match `hasAnyFilter` logic**

Replace:
```javascript
if(!state.appliedSearch){alert('Please enter a search query first.');return;}
```
With:
```javascript
const _hasFilter=!!(state.appliedSearch||state.filters.fromZone||state.filters.toZone||state.filters.tag);
if(!_hasFilter){alert('Please enter a search term or select a filter first.');return;}
```

---

### Task 10: Fix `copyDisplayLimit` reset value

**Files:**
- Modify: `NetSearch-prototype.html:2344`

- [ ] **Step 1: Change line 2344 from `copyDisplayLimit=200` to `copyDisplayLimit=50`**

The spec states the default is 50 and "See More" adds 50.

---

### Task 11: Final integration test

- [ ] **Step 1: Open `NetSearch-prototype.html` in browser**

- [ ] **Step 2: Import a firewall config + F5 config + FQDN CSV**

- [ ] **Step 3: Search for a known IP, switch to Copy tab**

Expected: "Generate Preview" button is enabled (search is set).

- [ ] **Step 4: Click "Generate Preview"**

Expected: Rows appear. If FQDN data was loaded, each row should anchor on a FQDN record. Rows with matching NAT (by prefix) should show `nat_name`, `nat_snat`, `nat_dnat`. F5-matched rows should show `f5_vs`, `f5_pool`, `f5_members` (not mixed up).

- [ ] **Step 5: Check the new fields are selectable in Field Settings**

Expected: `URL Category`, `NAT Zone From`, `NAT Zone To`, `Original Src`, `Original Dst`, `VS Port`, `VS Status` appear in the panel.

- [ ] **Step 6: Copy to clipboard and paste into Excel**

Expected: Multi-value fields (source, destination, pool members) appear as multi-line cells within a single Excel cell.

- [ ] **Step 7: Change the search query without regenerating**

Expected: Yellow "⚠️ Regenerate" hint appears.

- [ ] **Step 8: Change zone filter without regenerating**

Expected: Yellow hint still appears (dirty hint now tracks filters too).

- [ ] **Step 9: Clear all filters/search**

Expected: "Generate Preview" button becomes disabled.

- [ ] **Step 10: Verify total row count when > 50 — only 50 shown initially**

Expected: "Load More (50/N)" button appears. Each click adds 50 rows.
