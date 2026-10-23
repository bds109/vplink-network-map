import { createHash, randomUUID } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { basename, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepareAssociation } from './association.mjs';

export const CSV = 'VPL门店地图信息.csv';
export const SOURCE = 'map-data-source.json';
// Explicit grandfathered pre-provenance Production bytes, NOT a fallback for future releases.
// Keep this one-time baseline in sync with Gallery src/map-sync.js.
export const LEGACY_SOURCE_SHA256 = '93b940ad2f84eba438663b89fe49ed267843b2b401638b774039150a8e42387a';
export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
export function validateSource(value, sha256) {
  if (!value || value.schemaVersion !== 1 || value.csvSha256 !== sha256 ||
      !/^[0-9a-f-]{36}$/.test(value.dataVersion) ||
      Object.keys(value).sort().join(',') !== 'csvSha256,dataVersion,schemaVersion') throw new Error('SOURCE_METADATA_MISMATCH');
  return value;
}
export function validateFilename(filename) {
  if (typeof filename !== 'string' || !filename.trim() || filename.length > 240 || /[\x00-\x1f\x7f/\\]/.test(filename) || !/\.csv$/i.test(filename)) throw new Error('INVALID_ORIGINAL_FILENAME');
  return filename;
}
export function prepareSource(original, runtime, filename) {
  const record = prepareAssociation(original, runtime, validateFilename(filename), randomUUID());
  return { schemaVersion: 1, ...record };
}
export const publicSource = ({ schemaVersion, csvSha256, dataVersion }) => validateSource({ schemaVersion, csvSha256, dataVersion }, csvSha256);
// This only writes provenance. It never copies/replaces the production CSV or publishes anything.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 3) throw new Error('Usage: node scripts/gallery-sync/source.mjs /path/to/original-upload.csv');
  if (existsSync(SOURCE)) throw new Error('Existing provenance must be deliberately archived/removed before replacement');
  const original = process.argv[2];
  const source = prepareSource(readFileSync(original), readFileSync(CSV), basename(original));
  const directory = '.pi/map-data-sources'; mkdirSync(directory, { recursive: true, mode: 0o700 });
  const privateFile = join(directory, source.dataVersion + '.json');
  writeFileSync(privateFile, JSON.stringify(source, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  writeFileSync(SOURCE, JSON.stringify(publicSource(source), null, 2) + '\n', { flag: 'wx' });
  console.log(`Prepared opaque ${SOURCE} and private ${privateFile}. Never commit/upload the private record. Register it in existing D1 only with separate release authorization, then release CSV + opaque marker together.`);
}

// A real Pages build timestamp, never the upload/commit/preparation time. Fail closed if
// the exact data-release commit was skipped or its build receipt is no longer available.
export async function publicationReceipt(revision, getJson) {
  for (let page = 1; page <= 10; page++) {
    const builds = await getJson(`https://api.github.com/repos/bds109/vplink-network-map/pages/builds?per_page=100&page=${page}`);
    if (!Array.isArray(builds)) throw new Error('PAGES_RECEIPT_UNAVAILABLE');
    const match = builds.find(b => b.commit === revision && b.status === 'built');
    if (match && Number.isFinite(Date.parse(match.updated_at))) return new Date(match.updated_at).toISOString();
    if (builds.length < 100) break;
  }
  throw new Error('PAGES_RECEIPT_UNAVAILABLE');
}
