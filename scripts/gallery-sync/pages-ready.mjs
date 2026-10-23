// Read-only precondition for sync.mjs. No D1 client, Cloudflare token or sync invocation.
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export const BUDGET_MS = 180000;
export const INTERVAL_MS = 10000;
export const MAX_ATTEMPTS = 18;
export const FILES = { csv: 'VPL门店地图信息.csv', source: 'map-data-source.json', html: 'index.html' };
const REPOSITORY = 'bds109/vplink-network-map';
const PRODUCTION = 'https://map.vplink-automaten.de/';
export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
export class PagesReadyError extends Error {
  constructor(code, retryable = false) { super(code); this.code = code; this.retryable = retryable; }
}
const fail = code => { throw new PagesReadyError(code); };

export async function waitForPages({ revision, dataReleaseRevision, expected, readMain, readBuilds, readProduction,
  now = Date.now, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  budgetMs = BUDGET_MS, intervalMs = INTERVAL_MS, maxAttempts = MAX_ATTEMPTS, onProgress = () => {} }) {
  if (!/^[a-f0-9]{40}$/.test(revision || '')) fail('INVALID_REVISION');
  for (const key of Object.keys(FILES)) {
    if (!(key === 'source' && expected?.[key] === null) &&
        (!Buffer.isBuffer(expected?.[key]) || !expected[key].length)) fail('INVALID_EXPECTED_INPUT');
  }
  if (expected.source !== null && !/^[a-f0-9]{40}$/.test(dataReleaseRevision || '')) fail('DATA_RELEASE_REVISION_REQUIRED');
  const requiredRevisions = [...new Set([revision, ...(expected.source === null ? [] : [dataReleaseRevision])])];
  if (![budgetMs, intervalMs, maxAttempts].every(n => Number.isSafeInteger(n) && n > 0)) fail('INVALID_BUDGET');
  const started = now(), deadline = started + budgetMs;
  const report = { status: 'WAITING', revision, dataReleaseRevision:expected.source === null ? null : dataReleaseRevision, budgetMs, maxAttempts,
    expected: Object.fromEntries(Object.entries(expected).map(([k,v]) => [k,v === null ? null : digest(v)])), attempts: [] };
  const remaining = () => { const ms = deadline - now(); if (ms <= 0) fail('PAGES_READY_TIMEOUT'); return ms; };
  async function assertMain() {
    let current;
    const ms = remaining();
    try { current = await readMain(ms); }
    catch { fail('MAIN_UNVERIFIABLE'); }
    remaining();
    if (current !== revision) fail('MAIN_CHANGED');
  }
  const publish = () => onProgress(structuredClone({ ...report, elapsedMs: now() - started }));
  try {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      remaining(); await assertMain();
      const row = { attempt, status: 'WAITING' }; report.attempts.push(row);
      try {
        const builds = await readBuilds({ remainingMs: remaining(), attempt, requiredRevisions });
        remaining(); await assertMain();
        if (!Array.isArray(builds)) fail('PAGES_RECEIPT_INVALID');
        // API returns newest first. Do not accept an older successful rebuild if
        // the newest build for this same commit is now failed or still building.
        const receipts = requiredRevisions.map(sha => builds.find(b => b?.commit === sha));
        row.buildStatuses = Object.fromEntries(requiredRevisions.map((sha,i) => [sha,receipts[i]?.status || 'missing']));
        for (const build of receipts.filter(Boolean)) {
          if (['errored','failed','failure','cancelled'].includes(build.status) || build.error?.message) fail('PAGES_BUILD_FAILED');
          if (!['queued','pending','building','built'].includes(build.status)) fail('PAGES_RECEIPT_INVALID');
          if (build.status === 'built' && !Number.isFinite(Date.parse(build.updated_at))) fail('PAGES_RECEIPT_INVALID');
        }
        if (receipts.every(build => build?.status === 'built')) {
          row.inputs = {};
          for (const [key, filename] of Object.entries(FILES)) {
            const response = await readProduction({ key, filename, revision, attempt, remainingMs: remaining() });
            remaining(); await assertMain();
            if ([401,403].includes(response.status)) fail('PRODUCTION_INPUT_UNVERIFIABLE');
            const absent = expected[key] === null;
            const hash = response.status === 200 && Buffer.isBuffer(response.body) ? digest(response.body) : null;
            row.inputs[key] = { status: response.status, sha256: hash,
              matches: absent ? response.status === 404 : response.status === 200 && hash === report.expected[key] };
          }
          if (Object.values(row.inputs).every(input => input.matches)) {
            await assertMain();
            row.status = report.status = 'READY';
            const summarize = build => ({ commit:build.commit, status:build.status, updatedAt:build.updated_at });
            report.receipt = summarize(receipts[0]);
            if (expected.source !== null) report.dataReceipt = summarize(builds.find(b => b.commit === dataReleaseRevision));
            publish(); return { ...report, elapsedMs: now() - started };
          }
        }
      } catch (error) {
        if (!(error instanceof PagesReadyError) || !error.retryable) throw error;
        row.error = error.code;
        await assertMain();
      }
      publish();
      if (attempt === maxAttempts) fail('PAGES_READY_ATTEMPTS_EXHAUSTED');
      await sleep(Math.min(intervalMs, remaining()));
    }
  } catch (error) {
    report.status = 'BLOCKED';
    report.error = error instanceof PagesReadyError ? error.code : 'PAGES_READY_INTERNAL_ERROR';
    publish();
    throw new PagesReadyError(report.error);
  }
}

// Inputs must come from the exact checked-out commit, not a dirty worktree.
export function checkoutInputs(revision, git = args => execFileSync('git', args), read = readFileSync) {
  const names = git(['ls-tree','-rz','--name-only',revision,'--',...Object.values(FILES)]).toString().split('\0');
  return Object.fromEntries(Object.entries(FILES).map(([key, filename]) => {
    const committed = names.includes(filename) ? git(['show',`${revision}:${filename}`]) : null;
    let local;
    try { local = read(filename); } catch (error) { if (error.code !== 'ENOENT') throw error; local = null; }
    if ((!committed && key !== 'source') || (committed === null ? local !== null : !Buffer.isBuffer(local) || !local.equals(committed))) fail('CHECKOUT_INPUT_MISMATCH');
    return [key, committed];
  }));
}

export function readOnlyClients({ token, fetch = globalThis.fetch,
  git = (args, options) => execFileSync('git', args, options) }) {
  if (!token) fail('GITHUB_TOKEN_REQUIRED');
  async function get(url, remainingMs, api = false) {
    let response;
    try {
      response = await fetch(url, { method: 'GET', redirect: 'error',
        headers: { 'Cache-Control':'no-cache', ...(api ? { Authorization:`Bearer ${token}`,
          Accept:'application/vnd.github+json', 'X-GitHub-Api-Version':'2022-11-28' } : {}) },
        signal: AbortSignal.timeout(Math.max(1, Math.min(10000, remainingMs))) });
      const body = Buffer.from(await response.arrayBuffer());
      return { status:response.status, body };
    } catch { throw new PagesReadyError('READ_UNAVAILABLE', true); }
  }
  return {
    readMain(remainingMs) {
      return git(['ls-remote','origin','refs/heads/main'], { encoding:'utf8', timeout:Math.max(1,Math.min(10000,remainingMs)), maxBuffer:1024*1024 }).trim().split(/\s/)[0];
    },
    async readBuilds({ remainingMs, requiredRevisions = [] }) {
      const started = Date.now(), builds = [];
      // Match the existing provenance receipt search cap; never infer an older
      // data release from a later Preview/HTML commit or a missing receipt.
      for (let page = 1; page <= 10; page++) {
        const left = remainingMs - (Date.now() - started);
        if (left <= 0) fail('PAGES_READY_TIMEOUT');
        const response = await get(`https://api.github.com/repos/${REPOSITORY}/pages/builds?per_page=100&page=${page}`, left, true);
        if ([401,403,404].includes(response.status)) fail('PAGES_API_UNVERIFIABLE');
        if (response.status !== 200) throw new PagesReadyError('PAGES_API_UNAVAILABLE', true);
        let rows; try { rows = JSON.parse(response.body); } catch { fail('PAGES_RECEIPT_INVALID'); }
        if (!Array.isArray(rows)) fail('PAGES_RECEIPT_INVALID');
        builds.push(...rows);
        if (rows.length < 100 || !requiredRevisions.length || requiredRevisions.every(sha => builds.some(b => b?.commit === sha))) break;
      }
      return builds;
    },
    readProduction({ filename, revision, attempt, remainingMs }) {
      return get(`${PRODUCTION}${encodeURIComponent(filename)}?pagesReady=${revision}-${attempt}-${Date.now()}`, remainingMs);
    }
  };
}

async function cli() {
  const directory = 'gallery-sync-evidence'; mkdirSync(directory, { recursive:true });
  const event = ['push','schedule','workflow_dispatch'].includes(process.env.GITHUB_EVENT_NAME) ? process.env.GITHUB_EVENT_NAME : 'local';
  const save = report => writeFileSync(`${directory}/pages-ready.json`, JSON.stringify({ event, ...report },null,2));
  try {
    if (process.env.GITHUB_REPOSITORY && process.env.GITHUB_REPOSITORY !== REPOSITORY) fail('UNEXPECTED_REPOSITORY');
    const revision = execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
    if (execFileSync('git',['rev-parse','--is-shallow-repository'],{encoding:'utf8'}).trim() !== 'false') fail('SHALLOW_CHECKOUT');
    const expected = checkoutInputs(revision);
    const dataReleaseRevision = expected.source === null ? null : execFileSync('git',['log',revision,'-1','--format=%H','--',FILES.csv,FILES.source],{encoding:'utf8'}).trim();
    const clients = readOnlyClients({ token:process.env.GITHUB_TOKEN });
    const result = await waitForPages({ revision, dataReleaseRevision, expected, ...clients, onProgress:save });
    save(result);
    if (process.env.GITHUB_OUTPUT) writeFileSync(process.env.GITHUB_OUTPUT,'ready=true\n',{flag:'a'});
    console.log(JSON.stringify({ stage:'PAGES_READY', revision, attempts:result.attempts.length }));
  } catch (error) {
    const code = error instanceof PagesReadyError ? error.code : 'PAGES_READY_INTERNAL_ERROR';
    // Preserve detailed, redacted polling evidence when it already exists.
    let previous = {}; try { previous = JSON.parse(readFileSync(`${directory}/pages-ready.json`)); } catch {}
    save({ ...previous, status:'BLOCKED', error:code });
    console.error(`::error::Pages-ready blocked: ${code}. sync.mjs must not run; retry the full workflow on current main after publication is ready.`);
    process.exitCode = 1;
  }
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await cli();
