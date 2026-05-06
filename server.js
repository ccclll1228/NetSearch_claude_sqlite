'use strict';
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { parseConfig, parseFqdnFile } = require('./lib/parser');
const { startScheduler } = require('./lib/scheduler');
const { resolveDevicePaths } = require('./lib/discovery');
const { search: fqdnSearch, getLastSynced } = require('./lib/fqdn_db');

const settings = JSON.parse(fs.readFileSync('./config/settings.json', 'utf8'));

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ── In-memory state ──────────────────────────────────────────────────────────
const state = {
  parsedConfigs: [],   // [{ id, filename, parsed }]
  fqdnRecords:   [],   // [{ id, fqdn, domain, ip, owner, type, geoInfo }]
  lastLoaded:    null, // ISO string
  loading:       false,
};

const CACHE_PATH = path.join(__dirname, 'cache', 'parsed.json');

function readCache() {
  try {
    if (fs.existsSync(CACHE_PATH)) {
      const raw = fs.readFileSync(CACHE_PATH, 'utf8');
      const cached = JSON.parse(raw);
      state.parsedConfigs = cached.parsedConfigs || [];
      state.fqdnRecords   = cached.fqdnRecords   || [];
      state.lastLoaded    = cached.lastLoaded     || null;
      console.log(`[cache] Restored ${state.parsedConfigs.length} devices from cache (${state.lastLoaded})`);
    }
  } catch (err) {
    console.warn('[cache] Could not read cache:', err.message);
  }
}

function writeCache() {
  try {
    fs.mkdirSync(path.dirname(CACHE_PATH), { recursive: true });
    fs.writeFileSync(CACHE_PATH, JSON.stringify({
      parsedConfigs: state.parsedConfigs,
      fqdnRecords:   state.fqdnRecords,
      lastLoaded:    state.lastLoaded,
    }), 'utf8');
    console.log('[cache] Cache written.');
  } catch (err) {
    console.warn('[cache] Could not write cache:', err.message);
  }
}

// ── Loader ───────────────────────────────────────────────────────────────────
async function loadAllConfigs() {
  if (state.loading) return { ok: false, error: 'Already loading' };
  state.loading = true;
  console.log('[load] Starting config reload...');
  try {
    const newParsedConfigs = [];

    const resolvedFiles = resolveDevicePaths(settings.devices || [], settings.backupRoot);
    for (const entry of resolvedFiles) {
      const filePath = entry.path;
      if (!fs.existsSync(filePath)) {
        console.warn(`[load] File not found, skipping: ${filePath}`);
        continue;
      }
      const text = fs.readFileSync(filePath, 'utf8');
      const parsed = parseConfig(text);
      if (parsed.hostname && /^Unknown-/.test(parsed.hostname)) {
        const stem = path.basename(filePath)
          .replace(/\.[^.]+$/, '')
          .replace(/[_\-]+config$/i, '')
          .replace(/[_\-]+running$/i, '')
          .trim();
        if (stem) parsed.hostname = stem;
      }
      const id = `cfg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
      newParsedConfigs.push({ id, filename: path.basename(filePath), parsed });
      console.log(`[load] Parsed: ${parsed.hostname} (${parsed.type})`);
    }

    let newFqdnRecords = [];
    if (settings.fqdnFile && fs.existsSync(settings.fqdnFile)) {
      const text = fs.readFileSync(settings.fqdnFile, 'utf8');
      newFqdnRecords = parseFqdnFile(text);
      console.log(`[load] FQDN records: ${newFqdnRecords.length}`);
    }

    state.parsedConfigs = newParsedConfigs;
    state.fqdnRecords   = newFqdnRecords;
    state.lastLoaded    = new Date().toISOString();
    console.log(`[load] Done. ${newParsedConfigs.length} devices loaded.`);
    writeCache();
    return { ok: true, lastLoaded: state.lastLoaded };
  } catch (err) {
    console.error('[load] Error:', err.message);
    return { ok: false, error: err.message };
  } finally {
    state.loading = false;
  }
}

// ── API Routes ────────────────────────────────────────────────────────────────
app.get('/api/data', (req, res) => {
  res.json({
    parsedConfigs: state.parsedConfigs,
    fqdnRecords:   state.fqdnRecords,
    lastLoaded:    state.lastLoaded,
  });
});

app.get('/api/status', (req, res) => {
  res.json({
    lastLoaded: state.lastLoaded,
    loading:    state.loading,
    devices: state.parsedConfigs.map(c => ({
      hostname:  c.parsed.hostname,
      type:      c.parsed.type,
      ruleCount: (c.parsed.secRules || []).length,
    })),
  });
});

app.get('/api/fqdn', (req, res) => {
  const q = (req.query.q || '').trim();
  if (!q) return res.status(400).json({ error: 'Missing query parameter: q' });
  const limit = Math.min(parseInt(req.query.limit, 10) || 200, 1000);
  const rows = fqdnSearch(q, limit);
  res.json({ results: rows, lastSynced: getLastSynced(), total: rows.length });
});

app.post('/api/reload', async (req, res) => {
  const result = await loadAllConfigs();
  res.json(result);
});

// ── Startup ───────────────────────────────────────────────────────────────────
const PORT = settings.port || 3002;
const server = app.listen(PORT, async () => {
  console.log(`[server] NetSearch running at http://localhost:${PORT}`);
  readCache();
  loadAllConfigs();
  startScheduler(loadAllConfigs, settings.cronSchedule || []);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`[server] Port ${PORT} is already in use.`);
    console.error(`[server] Run this in PowerShell to free it:`);
    console.error(`[server]   Get-Process -Id (Get-NetTCPConnection -LocalPort ${PORT}).OwningProcess | Stop-Process -Force`);
    process.exit(1);
  } else {
    throw err;
  }
});
