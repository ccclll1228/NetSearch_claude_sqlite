# NetSearch

A network configuration visualizer for firewall and load-balancer devices.  
Parse and search across FortiGate, Palo Alto, Juniper SRX, and F5 LTM configurations from a single browser interface.

---

## Features

- Multi-device support: FortiGate, Palo Alto, Juniper SRX, F5 LTM
- Full-text search with boolean operators (`AND`, `OR`, `NOT`)
- Filter by From Zone / To Zone / Tag / Source / Destination
- Security Rules, NAT Rules, Routes, Objects, LTM VS/Pools tabs
- Symmetric chaining — find related rules by shared IPs
- FQDN record lookup with IP chaining
- Disabled rule dimming, tag badges, resizable NAT columns
- Auto-reload via cron schedule (default: 05:00 and 17:00)
- Parsed data cached to disk; served instantly on restart
- Drag-and-drop config debug mode (browser-only, no server needed)

---

## Requirements

- Node.js 18+
- npm

---

## Installation

```bash
git clone https://github.com/ccclll1228/NetSearch_claude.git
cd NetSearch_claude
npm install
```

---

## Configuration

Copy the example config and edit paths to your local config files:

```bash
cp config/settings.example.json config/settings.json
```

`config/settings.json` (not committed — contains local paths):

```json
{
  "port": 3000,
  "configFiles": [
    { "path": "/path/to/FW01.txt", "type": "auto" },
    { "path": "/path/to/LTM01.txt", "type": "auto" }
  ],
  "fqdnFile": "/path/to/all_fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

| Field | Description |
|-------|-------------|
| `port` | HTTP port (default: 3000) |
| `configFiles[].path` | Absolute path to device config file |
| `configFiles[].type` | `"auto"` or explicit: `"fortigate"`, `"paloalto"`, `"srx"`, `"f5"` |
| `fqdnFile` | Path to CSV with columns: `fqdn,ip,owner,...` |
| `cronSchedule` | Array of cron expressions for auto-reload |

---

## Usage

```bash
# Production
npm start

# Development (auto-restart on file change)
npm run dev
```

Open **http://localhost:3000** in your browser.

### Manual reload via API

```bash
curl -X POST http://localhost:3000/api/reload
curl http://localhost:3000/api/status
```

### Search syntax

| Example | Meaning |
|---------|---------|
| `10.0.0.1` | Match any field containing this IP |
| `"exact-name"` | Exact match |
| `web AND untrust` | Both terms must match |
| `web OR mail` | Either term matches |
| `NOT disabled` | Exclude matches |
| `192.168.1.0/24` | CIDR range match |

---

## File Structure

```
NetSearch_claude/
├── server.js                  # Express server, in-memory state, API routes
├── package.json
├── .gitignore
├── CLAUDE.md                  # AI coding guidance
├── lib/
│   ├── parser.js              # Config parsers (FortiGate, PaloAlto, SRX, F5)
│   └── scheduler.js           # node-cron auto-reload scheduler
├── public/
│   └── index.html             # Single-file frontend (CSS + JS + HTML inline)
├── config/
│   ├── settings.json          # Local config (gitignored)
│   └── settings.example.json  # Template
├── cache/
│   └── parsed.json            # Auto-generated cache (gitignored)
└── docs/
    └── superpowers/
        └── specs/             # Design specs
```

---

## Architecture

```mermaid
flowchart TD
    CF[Config Files\n.txt on disk] -->|startup + cron| SV[server.js\nExpress]
    SV -->|parseConfig / parseFqdnFile| PA[lib/parser.js]
    SV -->|startScheduler| SC[lib/scheduler.js]
    SC -->|cron trigger| SV
    SV -->|write| CA[(cache/parsed.json)]
    CA -->|read on restart| SV
    SV -->|GET /api/data| FE[public/index.html\nSingle-file Frontend]
    FE -->|search + filter| SE[Search Engine\nparseSearch / evaluateAST]
    SE -->|resolve objects| RE[resolveObject\nWeakMap cache]
    FE -->|render| UI[Tabs: SecRules / NAT / Routes\nObjects / LTM / Pools / Copy]
```

### Request flow

![Sequence diagram](docs/sequence.png)

| Phase | Description |
|-------|-------------|
| **Startup** | Server reads the disk cache immediately for a fast first response, then parses all device backup files in the background and writes an updated snapshot. |
| **Search request** | The browser fetches the full parsed dataset once, builds an in-memory search index, and runs `getFilteredData()` on every keystroke — no server round-trip per search. |
| **Reload** | A `POST /api/reload` (or the cron trigger at 05:00 / 17:00) re-parses all backup files and refreshes the disk cache without restarting the server. |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/data` | All parsed configs + FQDN records |
| `GET` | `/api/status` | Load status + device list |
| `POST` | `/api/reload` | Trigger immediate config reload |

---

## Supported Device Types

| Type | Detection | Key sections parsed |
|------|-----------|-------------------|
| FortiGate | `config firewall policy` | Policies, NAT, addresses, groups, routes |
| Palo Alto | `set security policies` | Security rules, NAT rules, address objects |
| Juniper SRX | `set security zones` | Security policies, SNAT/DNAT rule-sets |
| F5 LTM | `ltm virtual` | Virtual servers, pools, pool members |

---

## License

MIT
