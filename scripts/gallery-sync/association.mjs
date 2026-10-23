import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const normalizer = fileURLToPath(new URL('./normalize-source.py', import.meta.url));
export const NORMALIZER_SHA256 = digest(readFileSync(normalizer));
export function normalizeCSV(bytes) {
  try { return execFileSync('python3', [normalizer], { input: bytes, stdio: ['pipe', 'pipe', 'pipe'], maxBuffer: 16 * 1024 * 1024 }); }
  catch { throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED'); }
}
// The digest is an integrity binding, not a signature. Only the authorized D1
// publisher can register it, after replaying the conversion with both real files.
const binding = record => JSON.stringify([record.dataVersion, record.originalFilename, record.originalSha256, record.csvSha256, record.sourceProof.method, record.sourceProof.normalizerSha256]);
export function prepareAssociation(original, runtime, filename, version) {
  const identical = digest(original) === digest(runtime);
  if (!identical && digest(normalizeCSV(original)) !== digest(runtime)) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  const record = { recordVersion: 2, originalFilename: filename, originalSha256: digest(original), csvSha256: digest(runtime), dataVersion: version,
    sourceProof: { method: identical ? 'identity-v1' : 'csv-normalize-v1', normalizerSha256: identical ? null : NORMALIZER_SHA256 } };
  record.sourceProof.bindingSha256 = digest(binding(record));
  return record;
}
export function validateAssociation(record) {
  const p = record?.sourceProof;
  if (record?.recordVersion !== 2 || !/^[a-f0-9]{64}$/.test(record.originalSha256) || !/^[a-f0-9]{64}$/.test(record.csvSha256) ||
      !p || !['identity-v1', 'csv-normalize-v1'].includes(p.method) ||
      p.normalizerSha256 !== (p.method === 'identity-v1' ? null : NORMALIZER_SHA256) ||
      p.bindingSha256 !== digest(binding(record))) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  if (p.method === 'identity-v1' && record.originalSha256 !== record.csvSha256) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  return record;
}
export function verifyAssociation(record, original, runtime) {
  validateAssociation(record);
  if (!(original instanceof Uint8Array) || !(runtime instanceof Uint8Array) || digest(original) !== record.originalSha256 || digest(runtime) !== record.csvSha256 ||
      digest(record.sourceProof.method === 'identity-v1' ? original : normalizeCSV(original)) !== record.csvSha256) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  return record;
}
export function registrationRecord(row) {
  try {
    return validateAssociation({ recordVersion: 2, originalFilename: row.original_filename, originalSha256: row.original_sha256,
      csvSha256: row.source_sha256, dataVersion: row.data_version, sourceProof: JSON.parse(row.source_proof) });
  } catch { throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED'); }
}
