const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, '..', 'db', 'fqdn.db'));

const stmtSearch = db.prepare(`
  SELECT id, fqdn, ip, owner, domain, type, ttl, geo_info, synced_at
  FROM fqdn
  WHERE fqdn LIKE ? OR ip LIKE ? OR geo_info LIKE ?
  LIMIT ?
`);

const stmtLastSynced = db.prepare(`
  SELECT synced_at FROM fqdn ORDER BY id DESC LIMIT 1
`);

function search(keyword, limit = 200) {
  const pattern = `%${keyword}%`;
  return stmtSearch.all(pattern, pattern, pattern, limit);
}

function getLastSynced() {
  const row = stmtLastSynced.get();
  return row ? row.synced_at : null;
}

module.exports = { search, getLastSynced };
