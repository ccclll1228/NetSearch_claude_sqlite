# NetSearch — Architecture

## Module Relationship Diagram

```mermaid
flowchart TD
    subgraph Disk["Disk (local paths in settings.json)"]
        CF[/"Config Files\n.txt (FW / LTM)"/]
        FQ[/"FQDN CSV\nall_fqdn.csv"/]
        CA[("cache/\nparsed.json")]
        ST[/"config/\nsettings.json"/]
    end

    subgraph Server["server.js — Express Process"]
        direction TB
        ST -->|read on startup| SV[In-Memory State\nparsedConfigs\nfqdnRecords\nlastLoaded]
        SV -->|write after reload| CA
        CA -->|read on startup| SV
        AP1["GET /api/data"]
        AP2["GET /api/status"]
        AP3["POST /api/reload"]
    end

    subgraph Libs["lib/"]
        PA["parser.js\nparseConfig()\nparseFqdnFile()\n─────────────\nFortiGate parser\nPalo Alto parser\nSRX parser\nF5 parser"]
        SC["scheduler.js\nstartScheduler()\nnode-cron"]
    end

    subgraph Frontend["public/index.html — Browser"]
        direction TB
        FE["Init / Data Fetch\nGET /api/data"]
        SE["Search Engine\nparseSearch → AST\nevaluateAST"]
        MA["Matchers\nresolveObject (WeakMap)\n_matchNameOnly (Map)\nobjectListMatchesSearch"]
        FI["getFilteredData()\nfromZone / toZone / tag\nsrc / dst / disabled\nsymmetric chaining\nFQDN IP chaining"]
        RE["Renderers\nrenderSecRules\nrenderNatRules\nrenderRoutes\nrenderObjects\nrenderF5Virtuals\nrenderF5Pools\nrenderFqdnCopy"]
        PR["Inline Parsers\n(drag-drop debug only)"]
    end

    CF -->|loadAllConfigs| PA
    FQ -->|parseFqdnFile| PA
    PA -->|structured data| SV
    SC -->|cron trigger| SV
    SV --> AP1 & AP2 & AP3
    AP3 -->|trigger| PA
    AP1 -->|JSON| FE
    FE --> SE --> MA --> FI --> RE
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant D as Disk (config files)
    participant S as server.js
    participant C as cache/parsed.json
    participant B as Browser

    S->>C: read cache on startup (instant)
    S->>D: loadAllConfigs() async
    D-->>S: raw text
    S->>S: parseConfig() × N devices
    S->>C: writeCache()
    B->>S: GET /api/data
    S-->>B: { parsedConfigs, fqdnRecords, lastLoaded }
    B->>B: getFilteredData() on search/filter change
    B->>B: render tabs
    Note over S: cron 05:00 / 17:00
    S->>D: loadAllConfigs() again
    S->>C: writeCache()
```

---

## Parser Output Shape

All four parsers return the same normalized object:

```
{
  type:         string          // "FortiGate" | "PA" | "SRX" | "F5"
  hostname:     string
  addresses:    { name → string | string[] }
  groups:       { name → string[] }
  services:     { name → { protocol, port } }
  serviceGroups:{ name → string[] }
  secRules:     [{ name, disabled, action, from, to, source, destination,
                   application, service, category, tag }]
  natRules:     [{ name, disabled, from, to, source, destination,
                   service, tag, sourceTranslation, destinationTranslation }]
  routes:       [{ name, destination, nexthop, interface }]
  virtuals:     [{ name, ip, port, pool, ... }]   // F5 only
  pools:        [{ name, members }]               // F5 only
}
```

---

## Frontend Search Engine

```mermaid
flowchart LR
    IN["user input string"] --> PS["parseSearch()\nTokenizer + AST builder"]
    PS --> AST["AST Node\n{ op, left, right }\nor { term, exact }"]
    AST --> EV["evaluateAST()\nrecursive AND/OR/NOT"]
    EV --> MT["Matcher callbacks\nper-field checks"]
    MT --> RO["resolveObject()\nexpand address/group\nto { value, type } list"]
    RO --> WM["WeakMap cache\nkeyed on groups obj"]
```

### FQDN Tab Local Filter Pipeline

```mermaid
flowchart TD
    subgraph "FQDN Tab Local Filter"
        FI["Filter input\n(Enter to search)"] --> FPS["parseSearch()\nBoolean AST"]
        FPS --> FEV["evaluateAST()\nmatchFn per row"]
        FEV --> FIELDS["Match against:\nfqdn, ip, domain, geo_info"]
        FIELDS --> FOUT["fqdnDbFiltered()\nfiltered rows"]
    end

    subgraph "FQDN Data Source"
        API["/api/fqdn + /api/local_dns"] --> LOAD["fqdnDbAutoLoad()"]
        LOAD --> BASE["_fqdnBaseFilter()\nglobal search + device filter"]
        BASE --> FOUT
    end

    subgraph "Local Storage"
        LS["fqdnFilterHistory\n(max 10 entries)"] --> HIST["History dropdown\non focus when empty"]
        HIST --> FI
    end
```

### Key Frontend Functions

| Function | Responsibility |
|----------|---------------|
| `parseSearch()` | Tokenize and parse Boolean query into AST (AND/OR/NOT/quotes/parens) |
| `evaluateAST()` | Recursively evaluate AST against a record using a matchFn callback |
| `fqdnDbAutoLoad()` | Fetch FQDN data from `/api/fqdn` and `/api/local_dns`, merge results |
| `_fqdnBaseFilter()` | Apply global search keyword + device CIDR filter to fqdnDb rows |
| `fqdnDbFiltered()` | Apply FQDN local filter (Boolean AST) + type/owner/geo/ttl dropdowns |
| `fqdnDbInput()` | Track FQDN filter input value, update clear button visibility |
| `fqdnDbCommit()` | Save query to history, hide history dropdown, trigger render |
| `_fqdnFilterGetHistory()` | Read search history from `localStorage` (`fqdnFilterHistory`) |
| `_fqdnFilterSaveHistory()` | Deduplicate and save query to history (max 10 entries) |
| `fqdnFilterPickHistory()` | Fill input from history, execute search immediately |
| `getFilteredData()` | Main filter engine for all tabs (sec/nat/routes/objects/f5/fqdn) |
| `renderContent()` | Dispatch to per-tab renderers based on active tab |

---

## Symmetric Chaining & FQDN IP Matching

`getFilteredData()` builds two IP sets from matched rules for cross-tab chaining:

| Set | Cap | Used for |
|-----|-----|----------|
| `allRuleIps` | 50 entries | Routes, Addresses, Groups, F5 VS/Pools |
| `allRuleIpsForFqdn` | uncapped | FQDN tab only |

`allRuleIps` is capped to prevent O(N×M) freeze when iterating large rule/address sets.
`allRuleIpsForFqdn` is uncapped because FQDN matching is only IP-in-CIDR bitwise arithmetic —
CIDRs are pre-converted to `{num, mask}` pairs once before the FQDN record loop.

---

## Frontend DOM Patching Strategy

Pill expand/collapse avoids full `renderContent()` re-renders via targeted DOM patches:

| Operation | Method | Scope |
|-----------|--------|-------|
| Expand/Collapse All (sec/nat) | `_patchPillsChunked()` — rAF batches of 30 | All visible pills in tab |
| Expand/Collapse All (objects) | Direct `membersEl.innerHTML` replace | Object group rows |
| Single rule card expand/collapse | `_patchPidsDirect(pids)` — synchronous | Pills in that rule only |
| Individual nested node toggle | `_findRootPid()` → re-render root pill | One top-level pill |

Key internal maps (populated during `renderPills()`):

- `_pillContext` Map — pid → `{item, type, parsed, ctx}` — required for all DOM patches
- `_ruleExpandMap` — ruleKey → `{hostname, items, ctx}` — enumerate pills per rule card
- `_lastObjGroupMeta` — outerPid → `{g, addresses_dict, groups_dict}` — Objects fast-path
- `_patchGeneration` counter — incremented on every new patch or `renderContent(false)` to cancel stale rAF loops
