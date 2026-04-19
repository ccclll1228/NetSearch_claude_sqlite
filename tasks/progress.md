# IBM Carbon 改版進度

## ✅ 改版完成（2026-04-19）

所有 6 個 Batch 均已驗證通過。

---

## Batch 6 — Modal + Overlays + Utility Components ✅

### 摘要
- `.modal-overlay` → `rgba(0,0,0,0.5)`，移除 `backdrop-filter:blur`（Carbon 無毛玻璃）
- `.modal` → `#ffffff` 白底，`var(--cds-border-subtle)` border，0px radius，`box-shadow:0 4px 16px rgba(0,0,0,0.12)`
- `.modal-header` → `var(--cds-layer-02)` 底，`var(--cds-border-subtle)` bottom border，600 weight，`var(--cds-font-sans)`
- `.modal-close` → hover 加 `var(--cds-layer-hover)` bg
- `.dropzone` → `var(--cds-layer-02)` 底，`var(--cds-border-subtle)` 虛線 border；hover → `var(--cds-highlight)` + `var(--cds-interactive)`；移除 rgba cyan glow
- `.raw-config-header/pre` → `layer-02/layer-01` 底，0px radius，`font-sans/font-mono`
- `.bulk-textarea` → bottom-border only，focus → `outline:2px solid var(--cds-focus)`
- `.copy-feedback` → `#defbe6`（Green 10 solid）底，`var(--cds-text-primary)` 深色文字，✓ icon；移除 rgba 透明底
- `.search-help-popup` → `#ffffff` solid 底（防 rgba 透明問題），`box-shadow:0 8px 24px rgba(0,0,0,0.24)`；OR/AND/NOT badge 改 solid Green 10 / Red 10 / Blue 10 Carbon Tag
- `.search-hint` → `#e0e0e0`（Gray 20 solid）底全寬顯示，`var(--cds-text-secondary)` 文字，無邊框
- `.sh-badge` → Carbon Tag（24px radius），白字；keyword=Gray，ip=Blue 60，cidr=Teal，fqdn=Green
- `.scrollbar-thumb` → `var(--cds-border-subtle)` / `var(--cds-border-strong)`

---

## 前批次（已完成）

### Batch 5 — Pills + Object Cards + F5 Cards

### 摘要
- `.pill` → 0px radius，12px font，`var(--cds-background)` 底，`var(--cds-border-subtle)` border；matched → `var(--cds-highlight)` + `var(--cds-interactive)` text + rgba(15,98,254,0.30) border；hover → `var(--cds-layer-hover)` + `var(--cds-border-strong)`；移除 rgba cyan glow
- `.pill-detail` → 0px radius，`var(--cds-background)` 底，`var(--cds-border-subtle)` border；移除 `rgba(255,255,255,0.06)`
- `.pill-expand-header` → 0px radius，`var(--cds-interactive)` Blue 60 底，`#ffffff` 白字（舊版為 `color:#000`），hover → `var(--cds-interactive-hover)`
- `.pill-expand-body` → `border-left: 2px solid var(--cds-border-subtle)`；移除 `rgba(0,212,255,0.2)` cyan
- `.chain-pill` → Carbon Tag（24px radius）；fqdn = `support-success-bg` Green；nat = `highlight/interactive` Blue；dnat = `support-warning-bg` Yellow；各加 border
- `.rule-tag-chip` → Carbon Tag（24px radius），`var(--cds-layer-02)` 底，`var(--cds-text-secondary)` 字，`var(--cds-border-subtle)` border；移除 `rgba(160,130,255,...)` 紫色 rgba
- `.obj-card` → 明確換用 `var(--cds-layer-01)` + `var(--cds-border-subtle)` + `var(--cds-radius)`；移除 `--radius-sm` alias
- `.obj-card-type` → Carbon Tag（24px radius），`var(--cds-layer-02)` 底，`var(--cds-text-secondary)` 字，加 `var(--cds-border-subtle)` border
- `.obj-group-card` → 明確換用 `var(--cds-layer-01)` + `var(--cds-border-subtle)` + `var(--cds-radius)`
- `.f5-card` / `.f5-pool-card` → 明確換用 `var(--cds-layer-01)` + `var(--cds-border-subtle)` + `var(--cds-radius)`
- `.f5-pool-member-status` → Carbon Tag（24px radius），enabled = `support-success-bg` Green，disabled = `support-error-bg` Red；各加 border
- `.ltm-dot.enabled` → 移除 `box-shadow glow`，顏色改為 `var(--cds-support-success)`；disabled → `var(--cds-border-strong)`

### 已知問題 / 注意事項
- 無

---

## 前批次（已完成）

### Batch 4 — Rule Cards + Data Tables

### 摘要
- `.rule-card` → Carbon Tile：`var(--cds-layer-01)` 白底，`var(--cds-border-subtle)` border，0px radius，4px margin-bottom；hover 改為 `var(--cds-layer-hover)` 底 + `var(--cds-border-strong)` 邊框，**移除** cyan glow
- `.rule-card.allow-rule` → `border-left: 3px solid var(--cds-support-success)` Green 50
- `.rule-card.deny-rule`  → `border-left: 3px solid var(--cds-support-error)` Red 60
- `.rule-card.chained`    → `border-left: 3px solid var(--cds-support-warning)` Yellow 30，移除 gradient bg
- `.rule-card.rule-disabled` → `opacity:0.40; filter:grayscale(0.5)`，hover 回復至 `var(--cds-layer-hover)`
- `.rule-action` → Carbon Tag（24px radius）；allow = Green 50 bg；deny = Red 60 bg；移除 box-shadow
- `.rule-name` → `var(--cds-text-primary)`，`var(--cds-font-mono)`，`0.16px` tracking
- `.rule-device` → `var(--cds-text-secondary)`，11px
- `.rule-status` → Carbon Tag（24px radius），enabled/disabled 改用 support-success/error tokens
- `.rule-body-header` → `var(--cds-layer-02)` 底，`var(--cds-border-subtle)` border，12px/600/`var(--cds-font-sans)`
- `.rule-field + .rule-field` → `border-left: 1px solid var(--cds-border-subtle)`（舊版用 `rgba(255,255,255,0.03)`，在白底不可見）
- `.rule-field-label` → 11px/600，`var(--cds-text-secondary)`，`var(--cds-font-sans)`
- `.nat-col-header-row` → `var(--cds-layer-02)` 底，`var(--cds-border-subtle)` top/bottom border（舊用 `2px solid`）
- `.nat-col-head` → 12px/600，`var(--cds-font-sans)`
- `.nat-resize-handle` → 移除 box-shadow glow
- **Data Tables** (route/fqdn/f5-ltm) → `th`: `var(--cds-layer-02)` 底，`var(--cds-font-sans)` 12px/600，`#` `var(--cds-border-subtle)`；`td`: 8px padding，`var(--cds-border-subtle)` border；hover → `var(--cds-layer-hover)`
- `.device-group-header` → `var(--cds-layer-02)` 底，0px radius，hover 無 glow
- `.device-group-type` → Carbon Tag（24px radius），使用 `--cds-device-*` 語意 token
- `.device-type`（Modal） → 同 device-group-type，Carbon Tag + device tokens
- `.rule-copy-btn` → 0px radius，hover 改為 `var(--cds-highlight)` + `var(--cds-interactive)` text
- `.copy-field-btn` → Carbon Tag（24px radius，24px 高），selected = `var(--cds-highlight)` Blue 10
- `.copy-preview th/td` → Carbon Data Table header/cell 規格

### 已知問題 / 注意事項
- `rule-field + rule-field` 分隔線舊版為 `rgba(255,255,255,0.03)` — 在白底幾乎不可見；已改為 `var(--cds-border-subtle)` `#c6c6c6`，現在可見，屬預期行為
- chain-pill / rule-tag-chip 仍使用舊 rgba 顏色 — 在 Batch 5（Pills）會統一處理

---

### Batch 3 — Filter Bar + Device Chips + Tab Bar
- `.filter-bar` → 白底，8px 16px padding，border-subtle 下邊框
- `.device-toggle-btn` → Carbon Tag（24px radius），使用 device token
- `.filter-select` → bottom-border only，0px radius，Gray 10 底
- `.tab-btn` → 14px/400，Blue 60 active，移除 `::after`

### Batch 2 — Header / Masthead
- `.header` → `#161616` Gray 100，48px，無 gradient
- `.search-input` → `#262626` 底，bottom-border only，Blue 40 focus
- `.btn` / `.btn-primary` → 0px radius，Carbon Secondary/Primary

### Batch 1 — CSS tokens + 字型 + Base Styles
- 完整 `--cds-*` token 系統 + alias bridge
- 本地 IBM Plex 字型，body Gray 10 底

---

## 改版完成

所有 6 個 Batch 均已完成。IBM Carbon Design System 遷移完畢。

---

## 尚未開始批次

| Batch | 內容 |
|---|---|
| 6 | Modal + overlays + utility components |

---

## 累積變數對照表

| 舊變數 | 新 --cds-* token | 值 |
|---|---|---|
| `--bg` | `--cds-background` | `#f4f4f4` Gray 10 |
| `--bg-card` | `--cds-layer-01` | `#ffffff` White |
| `--bg-hover` | `--cds-layer-hover` | `#e8e8e8` |
| `--bg-elevated` | `--cds-layer-02` | `#e0e0e0` Gray 20 |
| `--border` | `--cds-border-subtle` | `#c6c6c6` Gray 30 |
| `--border-focus` | `--cds-focus` | `#0f62fe` Blue 60 |
| `--text` | `--cds-text-primary` | `#161616` Gray 100 |
| `--text-secondary` | `--cds-text-secondary` | `#525252` Gray 70 |
| `--text-muted` | `--cds-text-placeholder` | `#6f6f6f` Gray 60 |
| `--accent` | `--cds-interactive` | `#0f62fe` Blue 60 |
| `--accent-light` | `--cds-highlight` | `#edf5ff` Blue 10 |
| `--accent-hover` | `--cds-interactive-hover` | `#0353e9` |
| `--accent-glow` | — | `transparent` |
| `--green` | `--cds-support-success` | `#24a148` Green 50 |
| `--red` | `--cds-support-error` | `#da1e28` Red 60 |
| `--yellow` | `--cds-support-warning` | `#f1c21b` Yellow 30 |
| `--orange` | `--cds-support-caution` | `#ff832b` Orange 40 |
| `--blue` | `--cds-link-primary` | `#0f62fe` Blue 60 |
| `--pill-bg` | `--cds-background` | `#f4f4f4` Gray 10 |
| `--pill-match` | `--cds-highlight` | `#edf5ff` Blue 10 |
| `--radius` | `--cds-radius` | `0px` |
| `--radius-sm` | `--cds-radius` | `0px` |
| `--font-ui` | `--cds-font-sans` | IBM Plex Sans |
| `--font-mono` | `--cds-font-mono` | IBM Plex Mono |
