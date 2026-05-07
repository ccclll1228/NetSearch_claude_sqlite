const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, '..', 'db', 'fqdn.db'));

db.exec(`CREATE TABLE IF NOT EXISTS local_dns (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT,
  zone_name   TEXT,
  host_name   TEXT,
  record_type TEXT,
  record_data TEXT,
  synced_at   TEXT
)`);

const stmtSearch = db.prepare(`
  SELECT id, fqdn, ip, owner, domain, type, ttl, geo_info, synced_at
  FROM fqdn
  WHERE fqdn LIKE ? OR ip LIKE ? OR geo_info LIKE ?
  LIMIT ?
`);

const stmtSearchAll = db.prepare(`
  SELECT id, fqdn, ip, owner, domain, type, ttl, geo_info, synced_at
  FROM fqdn
  LIMIT ?
`);

const stmtLastSynced = db.prepare(`
  SELECT synced_at FROM fqdn ORDER BY id DESC LIMIT 1
`);

function search(keyword, limit = 200) {
  const pattern = `%${keyword}%`;
  return stmtSearch.all(pattern, pattern, pattern, limit);
}

function searchAll(limit = 10000) {
  return stmtSearchAll.all(limit);
}

function getLastSynced() {
  const row = stmtLastSynced.get();
  return row ? row.synced_at : null;
}

const stmtLocalDnsSearch = db.prepare(`
  SELECT id, source_file, zone_name, host_name, record_type, record_data, synced_at
  FROM local_dns
  WHERE zone_name LIKE ? OR host_name LIKE ? OR record_data LIKE ?
  LIMIT ?
`);

const stmtLocalDnsLastSynced = db.prepare(`
  SELECT synced_at FROM local_dns ORDER BY id DESC LIMIT 1
`);

function searchLocalDns(keyword, limit = 200) {
  const pattern = `%${keyword}%`;
  return stmtLocalDnsSearch.all(pattern, pattern, pattern, limit);
}

function getLocalDnsLastSynced() {
  const row = stmtLocalDnsLastSynced.get();
  return row ? row.synced_at : null;
}

module.exports = { search, searchAll, getLastSynced, searchLocalDns, getLocalDnsLastSynced };
