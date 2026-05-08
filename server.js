'use strict';
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { parseConfig } = require('./lib/parser');
const { startScheduler } = require('./lib/scheduler');
const { resolveDevicePaths } = require('./lib/discovery');
const { search: fqdnSearch, searchAll: fqdnSearchAll, getLastSynced, searchLocalDns, getLocalDnsLastSynced } = require('./lib/fqdn_db');

const settings = JSON.parse(fs.readFileSync('./config/settings.json', 'utf8'));

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ── In-memory state ──────────────────────────────────────────────────────────
const state = {
  parsedConfigs: [],   // [{ id, filename, parsed }]
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

    state.parsedConfigs = newParsedConfigs;
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
  const limit = Math.min(parseInt(req.query.limit, 10) || 200, 99999);
  const rows = q ? fqdnSearch(q, limit) : fqdnSearchAll(limit);
  res.json({ results: rows, lastSynced: getLastSynced(), total: rows.length });
});

app.get('/api/local_dns', (req, res) => {
  const q = (req.query.q || '').trim();
  if (!q) return res.json({ results: [], lastSynced: getLocalDnsLastSynced(), total: 0 });
  const limit = Math.min(parseInt(req.query.limit, 10) || 200, 99999);
  const rows = searchLocalDns(q, limit);
  res.json({ results: rows, lastSynced: getLocalDnsLastSynced(), total: rows.length });
});

app.post('/api/reload', async (req, res) => {
  const result = await loadAllConfigs();
  res.json(result);
});

app.get('/api/settings', (req, res) => {
  try {
    const s = JSON.parse(fs.readFileSync('./config/settings.json', 'utf8'));
    res.json({
      backupRoot:  s.backupRoot  || '',
      devices:     s.devices     || [],
      deviceTypes: s.deviceTypes || ['paloalto', 'f5', 'fortigate', 'srx'],
    });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/api/settings', (req, res) => {
  const { backupRoot, devices, deviceTypes } = req.body || {};
  if (!backupRoot || typeof backupRoot !== 'string' || !backupRoot.trim())
    return res.status(400).json({ ok: false, error: 'backupRoot is required' });
  if (!Array.isArray(devices))
    return res.status(400).json({ ok: false, error: 'devices must be an array' });
  for (const d of devices) {
    if (!d.name || !String(d.name).trim())
      return res.status(400).json({ ok: false, error: 'Each device must have a non-empty name' });
    if (!d.type || !String(d.type).trim())
      return res.status(400).json({ ok: false, error: `Device "${d.name}" must have a type` });
  }
  const names = devices.map(d => String(d.name).trim().toLowerCase());
  if (new Set(names).size !== names.length)
    return res.status(400).json({ ok: false, error: 'Duplicate device names are not allowed' });
  if (!Array.isArray(deviceTypes) || deviceTypes.length === 0)
    return res.status(400).json({ ok: false, error: 'deviceTypes must have at least one entry' });
  for (const t of deviceTypes)
    if (!t || !String(t).trim())
      return res.status(400).json({ ok: false, error: 'Device type cannot be empty' });
  try {
    const current = JSON.parse(fs.readFileSync('./config/settings.json', 'utf8'));
    const updated = {
      ...current,
      backupRoot:  backupRoot.trim(),
      devices:     devices.map(d => ({ name: String(d.name).trim(), type: String(d.type).trim() })),
      deviceTypes: deviceTypes.map(t => String(t).trim()),
    };
    fs.writeFileSync('./config/settings.json', JSON.stringify(updated, null, 2), 'utf8');
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
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
