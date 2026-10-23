import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { SOURCE, LEGACY_SOURCE_SHA256, validateSource, validateFilename, publicationReceipt } from './source.mjs';
import { registrationRecord } from './association.mjs';
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
export async function publishedProvenance(local, metadata, get, pause = sleep, attempts = 12) {
  let error;
  for (let i = 0; i < attempts; i++) {
    try {
      const sha = await publishedSource(local, get, pause, 1);
      const read = async url => {
        const bytes = await get(url);
        return bytes == null ? null : validateSource(JSON.parse(bytes.toString()), sha);
      };
      const github = await read(RAW + SOURCE + '?sync=' + Date.now());
      const production = await read('https://map.vplink-automaten.de/' + SOURCE + '?sync=' + Date.now());
      if (JSON.stringify(metadata) !== JSON.stringify(github) || JSON.stringify(metadata) !== JSON.stringify(production)) throw new Error('SOURCE_METADATA_MISMATCH');
      return sha;
    } catch (e) { error = e; }
    if (i + 1 < attempts) await pause(30000);
  }
  throw error;
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
// Dependency injection is used only by offline tests; the CLI supplies no overrides.
export async function main(test = {}) {
  const out = test.out || 'gallery-sync-evidence'; mkdirSync(out, { recursive: true });
  const report = { startedAt: new Date().toISOString(), revision: process.env.GITHUB_SHA || '', applicationRequests: 0, controlCalls: [], status: 'RUNNING' };
  const historyId = test.id || `${process.env.GITHUB_RUN_ID || randomUUID()}-${process.env.GITHUB_RUN_ATTEMPT || '1'}`;
  let historyStarted = false;
  let source = null;
  let local;
  let dataVersion;
  let releaseRevision;
  let publishedAt = null;
  let originalFilename = null, originalSha256 = null, sourceProof = null;
  const save = () => writeFileSync(`${out}/result.json`, JSON.stringify(report, null, 2));
  const get = test.get || (async url => {
    const r = await fetch(url, { headers: { 'Cache-Control': 'no-cache' }, signal: AbortSignal.timeout(45000) });
    if (r.status === 404 && new URL(url).pathname.endsWith('/' + SOURCE)) return null;
    if (!r.ok) throw new Error('Source fetch failed');
    return Buffer.from(await r.arrayBuffer());
  });
  async function query(sql, params = [], write = false) {
    if (test.query) return test.query(sql, params, write);
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
  const assertMain = test.assertMain || (() => {
    const current = execFileSync('git', ['ls-remote', 'origin', 'refs/heads/main'], { encoding: 'utf8' }).split(/\s/)[0];
    const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    if (current !== head) throw new Error('main moved during sync: rerun using current main');
    report.revision = head;
  });
  try {
    if (!test.query && !process.env.CLOUDFLARE_API_TOKEN) throw new Error('CLOUDFLARE_API_TOKEN is not configured');
    assertMain();
    local = test.local || readFileSync(CSV);
    report.sourceSha256 = hash(local);
    // Persist a non-success attempt BEFORE any source check or catalog write. If this
    // write is unavailable, abort: no business changes without a durable attempt.
    dataVersion = 'legacy';
    await query(`INSERT INTO map_sync_history(id,started_at,source_sha256,data_version,result) VALUES (?,?,?,?,'running')`, [historyId, report.startedAt, report.sourceSha256, dataVersion], true);
    historyStarted = true;
    try {
      const candidate = test.source === undefined ? JSON.parse(readFileSync(SOURCE, 'utf8')) : test.source;
      source = candidate === null ? null : validateSource(candidate, report.sourceSha256);
    }
    catch (e) { if (e.code !== 'ENOENT') throw e; }
    await publishedProvenance(local, source, get);
    releaseRevision = test.revision || execFileSync('git', ['log', '-1', '--format=%H', '--', CSV, SOURCE], { encoding: 'utf8' }).trim();
    dataVersion = source?.dataVersion || 'legacy';
    if (!source) {
      const modern = (await query("SELECT id FROM map_sync_history WHERE result='success' AND data_version!='legacy' LIMIT 1")).results.length;
      if (report.sourceSha256 !== (test.legacySourceSha256 || LEGACY_SOURCE_SHA256) || modern) throw new Error('PRIVATE_SOURCE_NOT_REGISTERED');
    }
    if (source) {
      const registration = (await query("SELECT * FROM map_sync_history WHERE id=? AND result='source' AND source_sha256=? AND data_version=?", ['source:' + dataVersion, report.sourceSha256, dataVersion])).results[0];
      if (!registration) throw new Error('PRIVATE_SOURCE_NOT_REGISTERED');
      const registered = registrationRecord(registration);
      originalFilename = validateFilename(registered.originalFilename);
      originalSha256 = registered.originalSha256; sourceProof = JSON.stringify(registered.sourceProof);
      publishedAt = test.receipt ? await test.receipt(releaseRevision) : await publicationReceipt(releaseRevision, async url => {
        const r = await fetch(url, { headers: { Authorization: `Bearer ${process.env.GITHUB_TOKEN}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' }, signal: AbortSignal.timeout(45000) });
        if (!r.ok) throw new Error('PAGES_RECEIPT_UNAVAILABLE');
        return r.json();
      });
      await query("UPDATE map_sync_history SET source_verified=1,published_at=?,release_revision=? WHERE id=? AND result='source' AND source_sha256=?", [publishedAt, releaseRevision, 'source:' + dataVersion, report.sourceSha256], true);
    }
    await query(`UPDATE map_sync_history SET original_filename=?,original_sha256=?,source_proof=?,data_version=?,release_revision=?,published_at=?,source_verified=1 WHERE id=? AND result='running'`, [originalFilename, originalSha256, sourceProof, dataVersion, releaseRevision, publishedAt, historyId], true);
    // Actions logs/artifacts are public-repository surfaces: the original name
    // remains only in private D1, never in console/summary/result.json.
    Object.assign(report, { dataVersion, releaseRevision, publishedAt });
    const data = test.data || JSON.parse(execFileSync('python3', [fileURLToPath(new URL('./read-map-catalog.py', import.meta.url)), CSV, 'index.html'], { encoding: 'utf8' }));
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
      await publishedProvenance(local, source, get, sleep, 2);
      const applied = await query(stmt.sql, stmt.params, true);
      if (applied.meta.changes !== stmt.expectedChanges) throw new Error('Concurrent catalog change: stopped; re-plan on retry');
      report.changed = applied.meta.changes;
    } else report.changed = 0;
    const after = (await query('SELECT * FROM stores ORDER BY id')).results;
    const final = guardPlan(after, data);
    if (catalogOperations(data, final).length) throw new Error('Post-sync catalog verification failed');
    report.afterCounts = (await query('SELECT (SELECT count(*) FROM stores) AS stores,(SELECT count(*) FROM photos) AS photos')).results[0];
    assertMain();
    await publishedProvenance(local, source, get, sleep, 2);
    // Confirm success only while the verified stores snapshot still matches. The
    // history write is deliberately last; uncertain writes leave running/failed,
    // never a fabricated success. A retry always re-reads and re-plans.
    const keys = Object.keys(after[0]).sort();
    const actual = keys.join(',');
    const expected = keys.map(k => `json_extract(value,'$.${k}')`).join(',');
    const stable = `NOT EXISTS (SELECT ${actual} FROM stores EXCEPT SELECT ${expected} FROM json_each(?6)) AND NOT EXISTS (SELECT ${expected} FROM json_each(?6) EXCEPT SELECT ${actual} FROM stores)`;
    const confirmed = await query(`UPDATE map_sync_history SET result='success',finished_at=?1,added_count=?2,updated_count=?3,disabled_count=?4 WHERE id=?5 AND result='running' AND (${stable})`, [new Date().toISOString(), plan.added.length, plan.updated.length, plan.absentFromProduction.length, historyId, JSON.stringify(after)], true);
    if (confirmed.meta.changes !== 1) throw new Error('HISTORY_CONFIRMATION_FAILED');
    report.status = 'PASS';
    console.log(JSON.stringify({ stage: 'VERIFIED', ...report }));
  } catch (error) {
    report.status = 'FAIL'; report.error = error.message;
    if (historyStarted) {
      try {
        const code = error.message === 'PRIVATE_SOURCE_NOT_REGISTERED' ? 'SOURCE_REGISTRATION_MISSING' : error.message === 'SOURCE_ASSOCIATION_NOT_VERIFIED' ? error.message : 'SYNC_FAILED';
        await query(`UPDATE map_sync_history SET result='failed',finished_at=?,error_code=? WHERE id=?`, [new Date().toISOString(), code, historyId], true);
        report.failureRecorded = true;
      } catch { report.failureRecorded = false; }
    }
    console.error('::error::Gallery catalog sync stopped safely; inspect result.json and rerun after resolving cause.');
    if (!test.query) process.exitCode = 1;
  } finally { report.finishedAt = new Date().toISOString(); save(); }
  return report;
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await main();
