# Changelog

All notable changes to NetSearch are documented here.

---

## [2.5.1] - 2026-05-14

### Fixed
- **FortiGate VIP group search — merge vipgrpMap into groups** — VIP group names (e.g. `vs2405_OFC_CSP_Log_API`) are now registered in `parsed.groups`, enabling proper destination-side matching through the search index, `resolveObject`, and `fqdnDeviceCidrRanges`
- **FortiGate source-only CIDR match suppressed for VIP rules** — when searching an exact IP, FortiGate rules with VIP destinations no longer false-positive on source CIDR containment alone; the destination VIP extip must also match
- **`import_local_dns.py` now reads TTL from CSV** — the local DNS CSV format added a TTL column; the sync script now parses it as an integer and stores it in `fqdn.ttl` instead of hardcoding `NULL`

### Added
- **TTL column in FQDN tab** — new column between TYPE and IP showing DNS TTL values; right-aligned with tabular-nums, sortable, included in Copy Columns picker and Copy tab FQDN field group
- **TTL filter dropdown in FQDN tab** — dropdown after the Geo filter populated with distinct TTL values sorted numerically; AND-combined with Type, Owner, and Geo filters; reset on Clear
- **Cascading FQDN filter dropdowns** — Geo and TTL dropdown options now depend on the selected Owner filter; changing Owner rebuilds the available Geo/TTL values from the owner-filtered subset and auto-resets stale selections; applied across all three FQDN render paths (fqdnDb, initial state, main)
- **Local font serving** — Inter, Cormorant Garamond, and JetBrains Mono woff2 files downloaded to `public/fonts/` with a local `fonts.css`; removes Google Fonts CDN dependency so the app works on isolated networks without internet access

### Changed
- **Tab bar readability** — inactive tabs use font-weight 600, active tab 700; badge counts use font-weight 700 with `tabular-nums` for clean alignment; horizontal padding reduced from 16px to 10px for a more compact layout

---

## [2.5.0] - 2026-05-11

### Fixed
- **DNAT→F5 chain fires for FQDN searches** — the DNAT-to-LTM chain previously only triggered for bare IP searches; now also fires when the search originates from an FQDN domain lookup
- **DNAT→LTM chain matches CIDR DNAT IPs when ignoreCIDR=true** — `/32` and other CIDR-notation DNAT IPs now match F5 virtual server IPs via base-IP comparison when ignoreCIDR is active
- **EXACT search mode implies ignoreCIDR for IP terms** — searching an IP in EXACT mode no longer matches CIDR ranges containing that IP; only exact base-IP equality is used
- **Service match no longer bypasses direction filter for IP searches** — in keyword fallback path, service matches were incorrectly included even when Src/Dst filter was active, causing false positives
- **Objects tab FQDN/Rule IP chaining guarded by search term type** — when searching for an IP address, the allFqdnIps and allRuleIps chain blocks in the Objects tab are now skipped, preventing false-positive address object matches from unrelated FQDN IPs
- **Objects tab FQDN/Rule IP chain matches CIDR address values** — chain blocks now use `matchObject` with `isExact=false` so CIDR address objects are included via containment matching
- **Copy tab FQDN data merged from SQLite** — `fqdnDb.results` from `/api/fqdn` are now merged into `fqdnRecords` so the Copy tab preview includes server-fetched FQDN records, not just local state
- **LTM Copy Row includes pool members** — copying an F5 virtual server row now appends pool members (IP:port + status) as indented sub-lines
- **Objects Address Group Copy walks full tree** — `copyGroupTree()` recursively walks nested address groups with indentation, replacing the previous flat member-list copy; circular references are guarded by a `seen` Set with depth limit 12
- **FQDN table column widths** — adjusted colgroup from 7 columns to 6 columns with wider DOMAIN/FQDN and percentage-based GEO column (15%)

### Added
- **Drag-and-drop reordering for Device Manager** — device rows in the Server Config tab can now be reordered by dragging the `⠿` handle; new order is persisted on Save & Reload
- **Source device tags collapse/expand** — tags exceeding 8 items collapse with a `+N more` chip; clicking expands to show all; 20% smaller tag size
- **Auto-trigger server reload on page open** — opening or refreshing the page triggers a `POST /api/reload` to ensure configs are current

### Changed
- **Design system migration** — full visual migration from IBM Carbon to Claude-inspired warm cream + coral palette: canvas `#faf9f5`, coral accent `#cc785c`, Inter/Cormorant Garamond/JetBrains Mono typography, `8px` border radius, serif logo treatment
- **DENY/ALLOW badges** — solid filled high-contrast badges (red `#c0392b` / green `#27ae60` with white text) replacing the previous outlined style
- **Favicon** — inline SVG dinosaur on coral background replacing the previous favicon

---

## [2.4.7] - 2026-05-08

### Fixed
- **Filter bar dropdowns — right padding increased to clear arrow** — `.filter-select` `padding-right` increased from `18px` to `20px` so option text no longer overlaps the custom SVG chevron (10px wide, anchored at `right 10px`).

---

## [2.4.6] - 2026-05-08

### Changed
- **Filter bar dropdowns — smaller font and tighter padding** — `.filter-select` `font-size` changed from `14px` to `0.75em` and `padding` from `0 32px 0 12px` to `2px 18px 2px 6px`, reducing the visual footprint of all filter dropdowns (FROM ZONE, TO ZONE, TAG, SCHEDULE, IP, RULE, F5) to match the denser filter bar layout. No HTML or JS changes.

---

## [2.4.5] - 2026-05-08

### Changed
- **Filter bar checkboxes replaced with dropdowns** — the three checkbox groups in the global filter bar are now `<select class="filter-select">` dropdowns matching the existing Carbon style (same as SCHEDULE, FROM ZONE, TO ZONE):
  - **IP (All / Src / Dst)** — replaces the separate Src and Dst checkboxes; selecting Src sets `filterSource=true`, Dst sets `filterDest=true`, All resets both
  - **RULE (All / Hide Disabled / Disabled Only)** — replaces the Hide Disabled + Disabled Only checkbox pair; selections map to `secHideDisabled`/`natHideDisabled` and `secShowDisabledOnly`/`natShowDisabledOnly` exactly as before
  - **F5 (All / Disabled Only)** — replaces the F5 Disabled checkbox; Disabled Only maps to `showDisabledMembersOnly=true`
  - All state variable names, filter logic, and renderer behavior are unchanged; the two separator `<span>` elements and five old `addEventListener` calls are removed; `clearAllFilters` resets via `.value = ''`

---

## [2.4.4] - 2026-05-08

### Changed
- **Static zone pills for FROM/TO columns** — `renderZonePills(list)` replaces `renderPills` for the FROM and TO cells in both Sec Rules and NAT Rules expanded rows. Zone names (e.g. `trust`, `untrust`) are now rendered as plain non-interactive `.pill` spans with no expand arrow, no search button, and no copy button. All other columns (SOURCE, DESTINATION, SERVICE, APPLICATION, TRANSLATION) are unchanged. Zone items remain in `_ruleExpandMap.expandableItems` but are silently skipped by `_patchPidsDirect` (`if (!pctx) continue`) — no re-render penalty.

---

## [2.4.3] - 2026-05-08

### Removed
- **Auto URL Import (Today's Backup)** — removed the hardcoded URL-fetch section from the Import modal. Deleted: HTML card (`urlImportBtn`, `urlImportStatus`, `urlImportResults`), `BASE_URL` constant, `BACKUP_CONFIGS` array, `fmtDate` helper, `buildFallbackCandidates` function, and `runUrlImport` async function. Manual drag-drop, config paste, Device Manager tab, and Reload button are unaffected.

---

## [2.4.2] - 2026-05-08

### Fixed
- **`lib/discovery.js` — case-insensitive folder and file matching** — site-folder regex now uses the `'i'` flag (`new RegExp(..., 'i')`) and the per-file `startsWith` check uses `.toLowerCase()` on both sides. Fixes devices whose backup folder name differs in case from the device name prefix (e.g. device `LoadTest-FW01` → folder `LOADTEST_20260508` on a case-sensitive Linux filesystem).

---

## [2.4.1] - 2026-05-08

### Docs
- **CLAUDE.md** — added `GET/POST /api/settings` to server routes list; added `deviceTypes` to configuration example and description; added Device Manager feature bullet
- **ARCHITECTURE.md** — expanded Config-file Data Flow with `GET/POST /api/settings`; added Device Manager block to Frontend Data Flow documenting `devMgr` state, `loadDevMgr`/`saveDevMgr` call chain, and modal structure

---

## [2.4.0] - 2026-05-08

### Added
- **Device Manager** — new Server Config tab in the Import modal for managing `config/settings.json` device list from the browser:
  - `GET /api/settings` — returns `{ backupRoot, devices, deviceTypes }` from `settings.json`; defaults `deviceTypes` to `["paloalto", "f5", "fortigate", "srx"]` if absent
  - `POST /api/settings` — validates and merges `{ backupRoot, devices, deviceTypes }` back into `settings.json`, preserving all other keys (`port`, `cronSchedule`, etc.)
  - Tab bar (`Import` | `Server Config`) at top of Import modal; existing Import tab content unchanged
  - `backupRoot` editable text field; device table with inline edit/delete/add; device type chips (× disabled when type is in use); Save & Reload button with `Saving… → Reloading… → Done. N device(s) loaded.` status feedback
  - `devMgr` local state object; all edits are isolated from global `state` until Save & Reload completes and `loadFromServer()` refreshes the page
  - `"deviceTypes"` field added to `config/settings.example.json`
  - Fully bilingual (EN / 中文); 16 new i18n keys; `applyLang()` re-renders the panel on language switch

---

## [2.3.2] - 2026-05-08

### Removed
- **`fqdnFile` CSV-load path** — the `settings.fqdnFile` key and all associated server-side logic have been removed. FQDN records are served exclusively via `db/fqdn.db` (populated by `ultradns.py` and `import_local_dns.py`). Removed from `server.js`: `parseFqdnFile` import, `state.fqdnRecords`, the file-read block in `loadAllConfigs()`, and `fqdnRecords` from cache and `/api/data` response. `"fqdnFile"` key removed from `config/settings.example.json`. `parseFqdnFile` in `lib/parser.js` and `public/index.html` is retained for manual drag-drop uploads.

---

## [2.3.1] - 2026-05-08

### Fixed
- **`ultradns.py` — zone-apex NS records now stored** — removed the `fqdn == zone_clean` guard in `_parse_rrset()` so NS records at the zone apex (e.g. `pdns1.ultradns.net.`) are inserted into the database alongside delegation NS records. Previously only sub-zone NS rows were kept.

---

## [2.3.0] - 2026-05-08

### Added
- **Schedule filter for Sec Rules** — new `SCHEDULE` dropdown in the global filter bar with three options: `SCHEDULE (All)` (default), `Scheduled Only`, `Unscheduled Only`. Applies only to the Sec Rules filtering pipeline; NAT Rules and all other tabs are unaffected. Composes with all existing filters. Implemented via `hasAppliedSchedule(rule)` utility (checks `rule.schedule` against `null`/`'always'`/`'none'`/`'any'`) and two guard lines in the sec rules loop. Fully bilingual (EN / 中文).

---

## [2.2.0] - 2026-05-08

### Added
- **Search loading indicator** — a CSS spinner + "Searching…" label appears above the results area on every search trigger across all tabs (Enter key, filter dropdowns, tab switch, search mode toggle, FQDN async fetch). On synchronous tabs a double `requestAnimationFrame` ensures at least one visible frame before the indicator hides, so users always get feedback that a search was received.
  - `<div id="search-loading">` inserted as a static sibling between `#tabBar` and `#content` — survives `el.innerHTML` replacement and works for both sync and async renders
  - Reuses the existing `@keyframes spin` animation; all colors use `--cds-*` tokens
  - `prefers-reduced-motion`: spinner animation disabled, "Searching…" text remains
  - `showLoading()` / `hideLoading()` wired into `renderContent()` full-render branch only; `expandOnly` calls (pill expand/collapse, device group toggle) excluded

---

## [2.1.0] - 2026-05-07

### Added
- **Local DNS CSV sync** (`import_local_dns.py`) — imports on-premise DNS records from `local_dns_csv/*.csv` into `db/fqdn.db` alongside UltraDNS records
  - Scans for newest CSV file only (alphabetical sort → last entry), preventing duplicate imports from multiple timestamped exports
  - Atomic per-file transactions: each file committed immediately on success; rollback on failure without stopping remaining files
  - Import-time filtering: hidden domains (`trz.prd`, `trz.uat`, `sso.trz`, `in-addr.arpa`) and hidden types (`PTR`, `SOA`, `WINS`) dropped before insert
  - `sync_all.sh` runs UltraDNS sync then Local DNS sync in sequence (`set -e`)
- **`GET /api/local_dns`** — new endpoint; searches LocalDNS rows by keyword with configurable limit
- **FQDN tab merges LocalDNS results** — `fqdnDbAutoLoad` fetches `/api/fqdn` and `/api/local_dns` in parallel; results are union-merged into the single FQDN table

### Fixed
- **FQDN tab — EXACT mode now applies strict equality** — in EXACT search mode the FQDN tab was doing substring matching (`includes`) instead of strict equality (`===`). Three locations patched in `_fqdnBaseFilter` and `fqdnDbFiltered`:
  - Direct keyword path: rows filtered to `=== kw` on `fqdn` or `ip`
  - OR-of-directs path: per-term match uses `===` in EXACT mode
  - Local text filter box: per-term match uses `===` on `fqdn`/`ip` only; domain and geo fields excluded from EXACT matching
- **FQDN tab — OR search works in global search bar** — queries like `taptap.asia OR taptap.zone` were treated as object/group names and fell into the IP-range filter path, returning no results. `_fqdnBaseFilter` now detects OR-of-direct-keywords and does text matching; `fqdnDbAutoLoad` fetches `/api/local_dns` once per OR term in parallel and unions results
- **FQDN tab — multi-device selection shows union** — selecting 2+ devices caused the device CIDR filter to return `[]` due to a `configs.length !== 1` guard; now iterates all active devices and accumulates a union of their destination CIDRs
- **FQDN result limit** — API endpoints `/api/fqdn` and `/api/local_dns` were truncating results at 10,000; limit raised to 99,999 in both frontend fetch calls and server-side `Math.min` cap

---

## [2.0.0] - 2026-04-19

### Changed — IBM Carbon Design System 全面改版

前端 UI 從自訂 Cyber 深色主題完整遷移至 IBM Carbon Design System（Light Theme）。所有 CSS 採 `--cds-*` token 命名，移除所有 rgba cyan/purple glow 殘留。

**主題架構**
- `--cds-*` token 系統 + alias bridge（`--bg`、`--accent` 等舊變數重導向至 `--cds-*`）
- 主題：`#161616` Masthead + `#f4f4f4` Gray 10 body + `#ffffff` White cards
- 字型：自架 IBM Plex Sans（UI）+ IBM Plex Mono（程式碼/IP）via `@fontsource`
- `--cds-radius: 0px`（Carbon 方角）；Carbon Tag 例外使用 `--cds-radius-tag: 24px`

**Masthead（Header）**
- `#161616` Gray 100 底，48px 高，無 gradient
- Search input：`#262626` 底，bottom-border only，Blue 40 focus
- Buttons：0px radius，Carbon Secondary/Primary

**Filter Bar + Device Chips + Tab Bar**
- Filter bar：`layer-01` 白底，`border-subtle` 下邊框
- Device toggle chips：Carbon Tag，`--cds-device-*` 語意 token（PA=Purple，FG=Red，F5=Blue，SRX=Teal）
- Tab bar：`layer-01` 底，Blue 60 active indicator，tab count badge 使用 `highlight` token

**Rule Cards + Data Tables**
- Rule card：Carbon Tile，`layer-01` 底，`border-subtle` border；allow/deny/chained 左邊框使用 `support-*` token；hover 移除 cyan glow
- Action badge：Carbon Tag，allow=Green 50，deny=Red 60
- NAT col header / Data table th：`layer-02` 底，`font-sans` 12px/600
- Device group header：`layer-02` 底，0px radius，hover 無 glow

**Pills + Object Cards + F5 Cards**
- Pill：`cds-background` 底，`border-subtle` border，0px radius；matched → `highlight` Blue 10
- Pill expand header：`cds-interactive` Blue 60 底，白色文字（移除舊版黑字）
- chain-pill：Carbon Tag，fqdn=Green / nat=Blue / dnat=Yellow
- rule-tag-chip：`layer-02` 底，`text-secondary`，移除紫色 rgba
- obj-card / f5-card / f5-pool-card：`layer-01` 底，0px radius
- f5-pool-member-status：Carbon Tag，support tokens
- ltm-dot：移除 glow

**Modal + Overlays + Utilities**
- Modal overlay：`rgba(0,0,0,0.5)`，移除 `backdrop-filter:blur`
- Modal：`#ffffff` 白底，modal-header `layer-02` 底
- Dropzone：`layer-02` 底，`border-subtle` 虛線；hover → `highlight` Blue 10
- Bulk textarea：bottom-border only，focus outline 2px Blue 60
- Copy feedback toast：`#defbe6`（Green 10 solid）底，深色文字，✓ icon
- Search help popup：`#ffffff` solid 底，加強 shadow，OR/AND/NOT badge 改 solid Carbon Tag
- Search hint bar：`#e0e0e0`（Gray 20）solid 底，全寬顯示，無邊框
- Search history sh-badge：Carbon Tag 白字，type 對應 cds token

---

## [1.9.0] - 2026-04-16

### Added
- **FQDN tab 一鍵複製篩選結果** — stats bar 新增 `Copy Columns ▾` 下拉選欄位 + `Copy` 按鈕：
  - `Copy Columns ▾`：點開後顯示 6 個欄位的勾選框（Owner、Domain、FQDN、Type、IP、Geo），預設勾選 FQDN + IP
  - 任意組合勾選後點 Copy，輸出 TSV 含 header 列，貼到 Excel 自動分欄
  - 勾選狀態在篩選 / 排序 re-render 間保留，不重置
  - 複製範圍為當前篩選全量（不受 2000 筆顯示上限影響）

### Fixed
- **FQDN 尾巴點（trailing dot）** — Domain、FQDN、IP 欄的結尾 `.` 在顯示、quickSearch、複製時一律去除（`customercare.asia.` → `customercare.asia`）；原始資料不動，搜尋 / 排序邏輯不受影響

---

## [1.8.0] - 2026-04-12

### Performance

- **Tab 切換加速（~80%）** — `switchTab()` 改傳 `expandOnly=true` 當快取有效時，跳過 `getFilteredData()` 重算
- **Objects tab 展開群組加速（~90%+）** — `togglePill()` 對 `obj_grp_*` pid 改為 targeted DOM patch：直接更新單一群組卡片的 members div，完全不觸發 `renderContent()`
- **群組 HTML 快取** — `_groupTreeHtmlCache` 記住每個已展開群組的 HTML 輸出，收合後再展開同一群組幾乎瞬間（`_groupTreeHtmlCache.clear()` 在每次全量 render 時清除）
- **Sec/NAT Rules pill 展開加速** — 新增 `renderOnePill()` helper、`_pillContext` map（pid → 渲染資料），`togglePill()` 改用 `querySelectorAll('[data-ppid]')` 就地替換 pill 的 `outerHTML`，不重繪整個規則 tab
- **NAT Rules 展開/收合按鈕** — 每條 NAT rule header 加入與 Sec Rules 一致的「展開全部」／「收合全部」按鈕；`renderPills()` 補上 `ruleKey` ctx，使各條規則 pill 展開狀態相互獨立，並套用 pill targeted patch 優化

---

## [1.7.0] - 2026-04-05

### Changed
- **SVG icon 取代 emoji** — Copy、Search（放大鏡）、Reload 三種操作圖示全面改用描邊 SVG，視覺風格與現有 Expand/Collapse icon 統一（`stroke`, `round linecap`, no fill）：
  - `SVG_COPY` — 雙矩形疊加（clipboard）
  - `SVG_QS` — circle + handle（放大鏡）
  - `SVG_RELOAD` — 270° 弧 + 箭頭尖端（重載）
  - 影響位置：header Bulk / Reload 按鈕、Copy tab「複製到剪貼簿」按鈕、Sec Rules / NAT Rules copy 按鈕、Objects 表格 copy 按鈕、Objects Group copy 按鈕、LTM VS copy 按鈕、所有 pill-qs 搜尋按鈕（17 處）、pill-cb copy 按鈕（1 處）
  - `applyLang()` 改用 `innerHTML` 渲染含 SVG 的按鈕文字
  - i18n 字串（en/zh）同步改為 template literal 引用 SVG 常數

---

## [1.6.0] - 2026-04-05

### Added
- **🔍 Quick Search 按鈕（Sec Rules pills）** — 所有 pill 統一改用 `.pill-qs` class，預設隱藏，hover 時顯示，點擊直接搜尋：
  - Collapsed pill：搜尋 object 名稱
  - Expanded header 行：搜尋 object 名稱
  - Expanded member 行：搜尋 value（IP/CIDR），fallback 到 name
  - URL Category pill：搜尋 category 名稱
  - 移除舊的 `.pill-quick-search` class，全面統一為 `.pill-qs`
- **🔍 Quick Search 按鈕（Objects / LTM / Pools tab）** — 擴展至三個 tab：
  - Objects Address 表格：name 欄、value 欄各一個 🔍
  - Objects Group header：搜尋 group 名稱
  - LTM VS：name 欄、IP 欄各一個 🔍
  - LTM pool member：搜尋純 IP
  - Pools pool header：搜尋 pool 名稱
  - Pools member：搜尋純 IP
- **🔍 Quick Search 按鈕（FQDN tab）** — DOMAIN、FQDN、IP 三欄各加 🔍 按鈕

### Fixed
- **FQDN Geo dropdown 亂值** — `parseFqdnFile` 新增 `isValidGeoInfo()` 清洗函數：長度 > 50、含 `=;@`、符合 IP 格式、開頭為 MX priority 數字、含兩個以上 `.` 的值一律清為空字串；`lib/parser.js` 與 `public/index.html` 同步修改
- **FQDN CSV pandas row-index 欄偏移** — header 偵測時過濾空字串欄位名稱，避免 pandas 輸出的空第 0 欄導致所有欄位 index 偏移 1
- **FQDN GEO 欄不顯示** — `fqdn-table` 改用 `table-layout:fixed` + `<colgroup>` 固定 7 欄比例（7/13/28/11/16/8/17%），防止 GEO 欄因全為空值被 browser 壓縮為 0 寬；`.fqdn-table td` 加 `word-break:break-all`

---

## [1.5.0] - 2026-04-05

### Fixed
- **Sec Rules 欄位標題覆蓋問題** — 向下捲動時 rule card 內容會蓋過 sticky 欄位標題列。根本原因：disabled rule card 的 `opacity`/`filter` 觸發 stacking context，在某些渲染路徑下覆蓋 sticky header。修正方式：`.rule-card` 加上 `position:relative; z-index:1`，`.rule-body-header` z-index 從 `3` 提升至 `10`，確保欄位標題永遠在最上層。

### Removed
- **`NetSearch-prototype.html`** — 原始單檔 prototype，功能已完整移植至 `server.js` + `public/index.html`，不再需要。
- **`requirements.txt`** — 以 Python pip 格式撰寫的 Node.js 依賴說明，內容與 `package.json` 重複且格式錯誤。
- **`docs/superpowers/`** — Backend 設計 spec 與實作計畫（`2026-04-04-netsearch-backend-design.md`、`2026-04-04-netsearch-backend.md`），功能已全數實作完成，僅為歷史文件。

---

## [1.4.0] - 2026-04-05

### Added
- **雙語 UI（繁體中文 / English）** — 完整 i18n 支援，點擊右上角語言按鈕即時切換，無需重新載入頁面。
  - 新增 `i18n` 物件（`en` / `zh` 兩套翻譯，共 80+ 個字串鍵值）
  - 新增 `T(key, ...args)` 翻譯函數，支援 `{0}`, `{1}` 參數插值
  - 新增 `applyLang()` 函數，更新所有靜態 HTML 元素（Header、篩選列、Modal）
  - 頁面初始化時即呼叫 `applyLang()`，確保初始語系正確

### Fixed
- **EN 語系顯示繁體字** — 狀態列（`資料版本：`、`載入中...`、`尚未載入`）及重載按鈕（`🔄 重載`、`重載中...`）過去硬編碼中文，現在依語系正確顯示
- **中文語系顯示英文** — 以下 UI 元素現在完整翻譯：
  - 篩選列：來源、FROM ZONE、TO ZONE、TAG、來源/目的 Checkbox、隱藏停用、只看停用、F5 停用、展開、收合、清除
  - 設備切換列：來源/全部 標籤
  - 各 Tab 統計列（共幾條規則、幾台設備）
  - 空白狀態文字（找不到符合的安全規則等）
  - 欄位標題（規則/動作、來源區、目的地等）
  - Objects 頁：地址、地址群組 標題及欄位名稱
  - F5 頁：VS 名稱、目的 IP、埠號、狀態
  - 搜尋提示（按 Enter 篩選）及搜尋歷史（最近搜尋、清除記錄）
  - 展開/收合所有物件 tooltip
  - 匯入 Modal、批次搜尋 Modal、確認對話框
  - Copy Tab：欄位設定、產生預覽、複製到剪貼簿等

---

## [1.3.0] - 2026-04-05

### Changed
- **Typography scale** — standardized font sizes from 10 chaotic values (`6.5/9/10/11/12/13/14/15/17/18px`) to a 7-step semantic scale:
  - `6.5px` — rule TAG chips (intentional, 50% of rule-name)
  - `10px` — column headers, badges, muted metadata, quick-search icon (was 9px in some places)
  - `11px` — pills, stats bar, secondary UI
  - `12px` — buttons, tables, form controls
  - `13px` — entity/object names (rule names, group names)
  - `14px` — body text
  - `16px` — device hostnames (was 15px)
  - `18px` — logo (was 17px)
- **CSS variables** — added `--fs-micro` through `--fs-disp` to `:root` for maintainability.

### Fixed
- **Layout overlaps** — search hint `bottom:-20px` changed to `top:calc(100% + 4px)` and header `padding-bottom:28px` added; eliminates hint text bleeding over Source device bar.
- **Copy tab** — preview panel header row uses `flex-wrap:wrap` so "Generate Preview" button wraps gracefully instead of overlapping "Preview" label on narrow viewports.

---

## [1.2.0] - 2026-04-05

### Added
- **Sticky column headers** — all tabs (Sec Rules, NAT Rules, Routes, FQDN, LTM, Pools) now freeze their column header row at `top:0` while scrolling through results. Backgrounds use solid `#141b2d` to prevent content bleed-through.
- **Objects tab: copy buttons** — each address row has a 📋 button (copies `name\tvalue`); each address group header has a 📋 button (copies group name + all members, one per line); each group member row has an individual 📋 button on hover.
- **Objects tab: full recursive tree** — expanding an address group now shows all nested sub-groups and their members in a fully-expanded tree (no additional clicks required). Uses `renderGroupTreeFull()` with circular reference guard (`_seen` Set, max depth 12).

### Changed
- **Expand / Collapse icons** — replaced `⊞`/`⊟` math symbols with SVG icons (four-corner expand / four-corner collapse) across all three locations: filter bar global buttons (`Expand` / `Collapse` labels added), per-rule buttons in Sec Rules card, and URL Category pill toggles. Previously used `➕`/`➖` emoji for URL Category.
- **Objects tab: address group members** — members now render in a vertical list (one per line) instead of horizontal pill wrap.
- **Objects tab: group expansion** — outer group toggle converted from DOM `classList.toggle` to `togglePill()` so that sub-group expansion (which calls `renderContent`) correctly preserves the outer group's open state.

### Fixed
- Sticky headers no longer overlap content — reverted accidental sticky on `.device-group-header` (device title bar) which caused z-index conflicts; only column header rows are sticky.
- `config/settings.json` Windows backslash paths replaced with forward slashes to fix `SyntaxError: Bad escaped character in JSON`.

---

## [1.1.0] - 2026-04-04

### Added
- **TAG badges** — security rules display tags below the rule name; NAT rules display tags beside the copy button. Font size is 50% of rule ID size (`6.5px`), styled as compact monospace chips.
- **NAT tab filters** — FROM ZONE, TO ZONE, and TAG filters now work correctly in the NAT Rules tab (previously only applied to Security Rules).
- **Tab-aware TAG dropdown** — switching to the NAT Rules tab populates the TAG filter with NAT rule tags; switching to Sec Rules tab shows security rule tags.
- **Zone dropdown includes NAT zones** — FROM ZONE / TO ZONE options now aggregate zones from both `secRules` and `natRules`.

### Changed
- **NAT column layout** — switched from fixed `px` widths to `fr` (fractional) units so columns fill the full container width at any screen size. Proportions now match Security Rules: `12fr 12fr 21fr 21fr 10fr 12fr 12fr`.
- **NAT column drag-resize** — resize math updated to convert `fr → px` using actual container width at drag start, giving intuitive pixel-accurate resizing.

---

## [1.0.0] - 2026-04-04

### Added — Backend (Phase 1 & 2)

- **Express server** (`server.js`) serving the frontend from `public/` and exposing three API endpoints:
  - `GET /api/data` — returns all parsed configs and FQDN records
  - `GET /api/status` — returns load status and per-device rule counts
  - `POST /api/reload` — triggers immediate config reload from disk
- **In-memory state** — `parsedConfigs[]`, `fqdnRecords[]`, `lastLoaded` held in process memory; served to all connected clients without re-parsing.
- **Disk cache** (`cache/parsed.json`) — written after every successful reload; read on server startup so the UI is immediately usable before the first parse completes.
- **Cron scheduler** (`lib/scheduler.js`) — auto-reloads configs on configurable cron expressions (default: `0 5 * * *` and `0 17 * * *`).
- **Config parsers extracted** to `lib/parser.js` — `parseConfig()` auto-detects device type; `parseFqdnFile()` parses CSV FQDN records.
- **Frontend data fetch** — `public/index.html` fetches from `GET /api/data` on load; falls back to empty state gracefully.
- **Port conflict error** — clear PowerShell command printed to console when port is already in use.

### Added — Frontend Improvements

- **Disabled rule styling** — disabled security and NAT rules are dimmed (`opacity: 0.38`, `grayscale(0.7)`). Rule name gains strikethrough. Hover restores partial visibility.
- **LTM expand/collapse fix** — ⊞/⊟ buttons now correctly operate `f5LtmExpandedRows` when on the LTM tab (previously modified the wrong state set).
- **LTM device group collapse fix** — ▶ header click now correctly matches `grp_${hostname}` key (previously used mismatched `grp_f5vs_` prefix).
- **NAT resizable columns** — sticky column header row with drag handles; columns resize independently without re-rendering rule cards.
- **SNAT/DNAT columns auto-show** — SNAT and DNAT columns only appear when at least one rule in the current result set has translation data.

### Performance

- **`allRuleIps` cap** — symmetric chaining IP set capped at 50 entries to prevent O(N×M) freeze when searching large address groups (e.g. 243-member groups).
- **`_matchNameOnly` cache** — `Map`-based cache added to recursive group name walk; cleared per `getFilteredData()` call.
- **`esc()` optimized** — HTML escaping switched from `createElement` (DOM allocation) to string `.replace()` chain.

---

## [0.1.0] - 2026-03-30 (Prototype)

- Single-file prototype (`NetSearch-prototype.html`) with all parsing and UI inline.
- FortiGate, Palo Alto, SRX, F5 config parsers.
- Boolean search engine with AST (`parseSearch`, `evaluateAST`).
- FQDN record lookup and IP chaining.
- Drag-and-drop config loading for local debug.
