# Changelog

All notable changes to NetSearch are documented here.

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
