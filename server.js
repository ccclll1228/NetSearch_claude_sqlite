'use strict';
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { parseConfig, parseFqdnFile } = require('./lib/parser');

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

// ── Loader ───────────────────────────────────────────────────────────────────
async function loadAllConfigs() {
  if (state.loading) return { ok: false, error: 'Already loading' };
  state.loading = true;
  console.log('[load] Starting config reload...');
  try {
    const newParsedConfigs = [];

    for (const entry of settings.configFiles) {
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

app.post('/api/reload', async (req, res) => {
  const result = await loadAllConfigs();
  res.json(result);
});

// ── Startup ───────────────────────────────────────────────────────────────────
const PORT = settings.port || 3000;
app.listen(PORT, async () => {
  console.log(`[server] NetSearch running at http://localhost:${PORT}`);
  await loadAllConfigs();
});
