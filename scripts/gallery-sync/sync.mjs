import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { planCatalog, catalogOperations } from './catalog.mjs';

export const ACCOUNT = '83e5af977d305636987c7e67119cffbd';
export const DATABASE = 'ab3bb1a5-eb91-4092-a5d6-cc0b43b792e1';
const CSV = 'VPL门店地图信息.csv';
const PRODUCTION = 'https://map.vplink-automaten.de/' + encodeURIComponent(CSV);
const RAW = 'https://raw.githubusercontent.com/bds109/vplink-network-map/main/';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
export function validate(data) {
  if (!['Category', 'Geekbar', 'Dojo'].every(k => data.columns.includes(k))) throw new Error('Missing catalog/brand columns');
  if (data.invalidRows.length || !data.stores.length) throw new Error('Invalid nonblank rows or empty catalog');
}
export function guardPlan(existing, data) {
  validate(data);
  const plan = planCatalog(existing, data);
  if (plan.conflicts.length) throw new Error('Catalog ID/source conflict: manual review required');
  const active = existing.filter(s => s.catalog_source === 'production' && s.map_present).length;
  // More than 5 stores OR more than 10% of present stores requires a separately reviewed code change.
  if (plan.absentFromProduction.length > 5 || plan.absentFromProduction.length > active * 0.10) throw new Error('Major removal blocked');
  return plan;
}
export function atomicStatement(existing, data, plan) {
  const ops = catalogOperations(data, plan);
  if (!ops.length) return null;
  const insert = ops.find(op => op.sql.startsWith('INSERT'));
  const columns = (insert?.sql.match(/stores\(([^)]+)\)/)?.[1] || 'id,name,city,state,map_id,postal_code,address,latitude,longitude,store_type,category,geekbar,dojo,catalog_source,map_present,source_sha256,catalog_active').split(',');
  const rows = ops.map(op => {
    if (op.sql.startsWith('INSERT')) return op.params;
    const old = existing.find(s => s.id === op.params[0]);
    return columns.map(c => c === 'map_present' ? 0 : old[c]);
  });
  // Compare the entire stores snapshot inside the same statement. A concurrent writer causes 0 changes.
  const keys = Object.keys(existing[0] || {}).sort();
  if (!keys.length || !keys.every(k => /^[a-z_][a-z_0-9]*$/.test(k))) throw new Error('Unexpected/empty production schema');
  const expected = keys.map(k => `json_extract(value,'$.${k}')`).join(',');
  const actual = keys.join(',');
  const stable = `NOT EXISTS (SELECT ${actual} FROM stores EXCEPT SELECT ${expected} FROM json_each(?2)) AND NOT EXISTS (SELECT ${expected} FROM json_each(?2) EXCEPT SELECT ${actual} FROM stores)`;
  const sql = `INSERT INTO stores(${columns.join(',')}) SELECT ${columns.map((_, i) => `json_extract(value,'$[${i}]')`).join(',')} FROM json_each(?1) WHERE (${stable}) ON CONFLICT(id) DO UPDATE SET ${columns.slice(1).map(c => `${c}=excluded.${c}`).join(',')}`;
  return { sql, params: [JSON.stringify(rows), JSON.stringify(existing)], expectedChanges: rows.length };
}
export async function publishedSource(local, get, pause = sleep, attempts = 12) {
  for (let i = 0; i < attempts; i++) {
    try {
      const github = await get(RAW + encodeURIComponent(CSV) + '?sync=' + Date.now());
      const production = await get(PRODUCTION + '?gallerySync=' + Date.now());
      if (hash(local) === hash(github) && hash(github) === hash(production)) return hash(local);
      console.log(JSON.stringify({ stage: 'WAIT_FOR_PAGES', attempt: i + 1, expectedSha256: hash(local), githubSha256: hash(github), productionSha256: hash(production) }));
    } catch { console.log(JSON.stringify({ stage: 'SOURCE_FETCH_RETRY', attempt: i + 1 })); }
    if (i + 1 < attempts) await pause(30000);
  }
  throw new Error('Published Production CSV does not match current GitHub main; no D1 write');
}
export async function main() {
  const out = 'gallery-sync-evidence'; mkdirSync(out, { recursive: true });
  const report = { startedAt: new Date().toISOString(), revision: process.env.GITHUB_SHA || '', applicationRequests: 0, controlCalls: [], status: 'RUNNING' };
  const save = () => writeFileSync(`${out}/result.json`, JSON.stringify(report, null, 2));
  const get = async url => {
    const r = await fetch(url, { headers: { 'Cache-Control': 'no-cache' }, signal: AbortSignal.timeout(45000) });
    if (!r.ok) throw new Error('Source fetch failed');
    return Buffer.from(await r.arrayBuffer());
  };
  async function query(sql, params = [], write = false) {
    const entry = { at: new Date().toISOString(), method: 'POST', resource: 'D1/query', write, status: 'STARTED' };
    report.controlCalls.push(entry); save();
    try {
      const r = await fetch(`https://api.cloudflare.com/client/v4/accounts/${ACCOUNT}/d1/database/${DATABASE}/query`, {
        method: 'POST', headers: { Authorization: `Bearer ${process.env.CLOUDFLARE_API_TOKEN}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql, params }), signal: AbortSignal.timeout(45000)
      });
      entry.httpStatus = r.status;
      const j = await r.json();
      if (!r.ok || !j.success || !j.result?.every(x => x.success)) throw new Error('D1 control query rejected');
      entry.status = 'OK'; save(); return j.result[0];
    } catch { entry.status = 'FAILED_OR_UNCERTAIN'; save(); throw new Error('D1 call failed; rerun whole workflow to re-read/re-plan, never replay a stale write'); }
  }
  const assertMain = () => {
    const current = execFileSync('git', ['ls-remote', 'origin', 'refs/heads/main'], { encoding: 'utf8' }).split(/\s/)[0];
    const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    if (current !== head) throw new Error('main moved during sync: rerun using current main');
    report.revision = head;
  };
  try {
    if (!process.env.CLOUDFLARE_API_TOKEN) throw new Error('CLOUDFLARE_API_TOKEN is not configured');
    assertMain();
    const local = readFileSync(CSV);
    report.sourceSha256 = await publishedSource(local, get);
    const data = JSON.parse(execFileSync('python3', [fileURLToPath(new URL('./read-map-catalog.py', import.meta.url)), CSV, 'index.html'], { encoding: 'utf8' }));
    validate(data);
    const before = (await query('SELECT * FROM stores ORDER BY id')).results;
    const counts = await query('SELECT (SELECT count(*) FROM stores) AS stores,(SELECT count(*) FROM photos) AS photos');
    report.beforeCounts = counts.results[0];
    const plan = guardPlan(before, data);
    report.plan = { added: plan.added.map(x => x.id), updated: plan.updated.map(x => ({ id: x.id, fields: x.fields })), absent: plan.absentFromProduction, unchanged: plan.unchanged.length, isolatedLegacy: plan.isolatedLegacy };
    save();
    const stmt = atomicStatement(before, data, plan);
    if (stmt) {
      assertMain();
      await publishedSource(local, get, sleep, 2);
      const applied = await query(stmt.sql, stmt.params, true);
      if (applied.meta.changes !== stmt.expectedChanges) throw new Error('Concurrent catalog change: stopped; re-plan on retry');
      report.changed = applied.meta.changes;
    } else report.changed = 0;
    const after = (await query('SELECT * FROM stores ORDER BY id')).results;
    const final = guardPlan(after, data);
    if (catalogOperations(data, final).length) throw new Error('Post-sync catalog verification failed');
    report.afterCounts = (await query('SELECT (SELECT count(*) FROM stores) AS stores,(SELECT count(*) FROM photos) AS photos')).results[0];
    report.status = 'PASS';
    console.log(JSON.stringify({ stage: 'VERIFIED', ...report }));
  } catch (error) {
    report.status = 'FAIL'; report.error = error.message;
    console.error('::error::Gallery catalog sync stopped safely; inspect result.json and rerun after resolving cause.');
    process.exitCode = 1;
  } finally { report.finishedAt = new Date().toISOString(); save(); }
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await main();
