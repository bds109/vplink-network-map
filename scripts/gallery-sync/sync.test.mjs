import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { planCatalog, catalogOperations } from './catalog.mjs';
import { atomicStatement, guardPlan, publishedSource } from './sync.mjs';

const parsed = JSON.parse(execFileSync('python3', ['scripts/gallery-sync/read-map-catalog.py', 'VPL门店地图信息.csv', 'index.html'], { encoding: 'utf8' }));
// Mutation tests use a fixed synthetic catalog, independent of future production counts/IDs.
const base = { ...parsed, valid: 20, stores: Array.from({ length: 20 }, (_, i) => ({ ...parsed.stores[0], id: String(10001 + i), mapId: String(10001 + i), name: `Isolation store ${i}` })) };
function existing(data = base) {
  const ops = catalogOperations(data, planCatalog([], data));
  const columns = ops[0].sql.match(/stores\(([^)]+)\)/)[1].split(',');
  return ops.map(op => Object.fromEntries(columns.map((c, i) => [c, op.params[i]])));
}
const copy = x => structuredClone(x);
function apply(old, data, mutate = null, fail = false) {
  const plan = guardPlan(old, data), stmt = atomicStatement(old, data, plan);
  if (!stmt) return { rows: old, changes: 0, protected: true };
  // Actual SQLite execution, foreign keys and trigger-based failure injection; no mocks of SQL semantics.
  return JSON.parse(execFileSync('python3', ['-c', `
import sqlite3,json,sys
x=json.load(sys.stdin); db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
cols=list(x['old'][0]); db.execute('PRAGMA foreign_keys=ON')
db.execute('CREATE TABLE stores('+','.join(c+(' TEXT PRIMARY KEY' if c=='id' else ' REAL' if c in ['latitude','longitude'] else ' INTEGER' if c in ['geekbar','dojo','map_present','catalog_active'] else ' TEXT') for c in cols)+')')
for row in x['old']: db.execute('INSERT INTO stores VALUES('+','.join('?' for c in cols)+')',[row[c] for c in cols])
db.execute('CREATE TABLE photos(id TEXT PRIMARY KEY,store_id TEXT REFERENCES stores(id),object_key TEXT)')
db.execute('INSERT INTO photos VALUES(?,?,?)',('preserved',x['old'][0]['id'],'unchanged-original'))
db.execute('CREATE TABLE customers(id TEXT,password TEXT)');db.execute("INSERT INTO customers VALUES('brand','unchanged-secret')")
if x['mutate']: db.execute('UPDATE stores SET name=? WHERE id=?',x['mutate'])
db.commit()
if x['fail']: db.execute("CREATE TRIGGER injected BEFORE UPDATE ON stores BEGIN SELECT RAISE(ABORT,'injected'); END")
error=None
try:
 db.execute(x['stmt']['sql'],x['stmt']['params']);changes=db.execute('SELECT changes()').fetchone()[0];db.commit()
except sqlite3.DatabaseError:
 db.rollback();changes=0;error='injected'
print(json.dumps({'rows':[dict(r) for r in db.execute('SELECT * FROM stores ORDER BY id')], 'changes':changes,'error':error,'protected': db.execute('SELECT count(*) FROM photos WHERE object_key=?',('unchanged-original',)).fetchone()[0]==1 and db.execute('SELECT password FROM customers').fetchone()[0]=='unchanged-secret' and not list(db.execute('PRAGMA foreign_key_check'))}))
`], { input: JSON.stringify({ old, stmt, mutate, fail }), encoding: 'utf8' }));
}

test('production parser validates current data without freezing future counts or flags', () => {
  assert.ok(parsed.valid > 0); assert.equal(parsed.invalidRows.length, 0);
  assert.equal(parsed.valid, parsed.stores.length);
  assert.equal(new Set(parsed.stores.map(s => s.id)).size, parsed.valid);
  assert.ok(parsed.stores.every(s => [0, 1].includes(s.dojo) && [0, 1].includes(s.geekbar)));
  assert.equal(atomicStatement(existing(parsed), parsed, guardPlan(existing(parsed), parsed)), null);
});
test('SQLite add + modify + remove atomically; preserve photo ownership and customer', () => {
  const data = copy(base), old = existing(), removed = data.stores.shift().id;
  data.stores[0].name += ' updated'; data.stores.push({ ...data.stores[1], id: '987654', mapId: '987654' });
  const result = apply(old, data);
  assert.equal(result.changes, 3); assert.equal(result.rows.length, base.stores.length + 1); assert.ok(result.protected);
  assert.equal(result.rows.find(s => s.id === removed).map_present, 0);
  assert.equal(result.rows.find(s => s.id === removed).catalog_active, 1); // existing Gallery contract uses map_present AND active
  assert.equal(catalogOperations(data, guardPlan(result.rows, data)).length, 0);
  const restored = apply(result.rows, base); assert.ok(restored.protected);
  assert.equal(restored.rows.find(s => s.id === removed).map_present, 1);
});
test('absent-only statement and restore retain history; repeat is no-op', () => {
  const data = copy(base); const removed = data.stores.shift().id;
  const result = apply(existing(), data); assert.equal(result.changes, 1); assert.ok(result.protected);
  assert.equal(result.rows.find(s => s.id === removed).map_present, 0);
  assert.equal(apply(result.rows, data).changes, 0);
  const restored = apply(result.rows, base); assert.equal(restored.changes, 1);
});
test('major removal, invalid rows, missing brand, duplicate IDs and conflicts blocked', () => {
  for (const change of [d => d.stores.splice(0, 6), d => d.invalidRows.push(3), d => d.columns.splice(d.columns.indexOf('Dojo'), 1), d => d.stores.push(d.stores[0])]) {
    const d = copy(base); change(d); assert.throws(() => guardPlan(existing(), d));
  }
  const old = existing(); old[0].catalog_source = 'legacy'; old[0].name = 'unknown';
  assert.throws(() => guardPlan(old, base));
});
test('optimistic snapshot guard rejects concurrent catalog edit, retry re-plans', () => {
  const d = copy(base); d.stores[0].city += ' edited';
  const old = existing(); const result = apply(old, d, ['concurrent name', old[1].id]);
  assert.equal(result.changes, 0); assert.equal(result.rows.find(s => s.id === old[0].id).city, old[0].city);
  assert.equal(apply(result.rows, d).changes, 2);
});
test('injected SQL failure rolls back entire statement, fresh retry succeeds and is idempotent', () => {
  const d = copy(base); d.stores[0].name += ' changed'; d.stores[1].name += ' changed';
  const old = existing(); const result = apply(old, d, null, true);
  assert.equal(result.error, 'injected'); assert.equal(result.changes, 0); assert.ok(result.protected);
  assert.deepEqual(result.rows, [...old].sort((a, b) => a.id.localeCompare(b.id)));
  const retry = apply(result.rows, d); assert.equal(retry.changes, 2); assert.equal(apply(retry.rows, d).changes, 0);
});
test('published source gate waits for exact bytes and rejects stale/failed sources', async () => {
  const local = Buffer.from('new'), stale = Buffer.from('old'); let calls = 0;
  await publishedSource(local, async () => ++calls <= 2 ? stale : local, async () => {}, 2);
  assert.equal(calls, 4);
  await assert.rejects(publishedSource(local, async () => stale, async () => {}, 2));
  await assert.rejects(publishedSource(local, async () => { throw new Error('network'); }, async () => {}, 2));
});
test('vendored logic contains no runtime import, token or Gallery local dependency', () => {
  assert.ok(!readFileSync('scripts/gallery-sync/catalog.mjs', 'utf8').includes("from './runtime"));
});
