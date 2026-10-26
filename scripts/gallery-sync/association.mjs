import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const normalizer = fileURLToPath(new URL('./normalize-source.py', import.meta.url));
export const NORMALIZER_SHA256 = digest(readFileSync(normalizer));
const xlsxConverter = fileURLToPath(new URL('./xlsx-sheet.py', import.meta.url));
export const XLSX_CONVERTER_SHA256 = digest(readFileSync(xlsxConverter));
export function normalizeXLSX(bytes, worksheet) {
  if (typeof worksheet !== 'string' || !worksheet || worksheet.length > 31 || /[\x00-\x1f\x7f]/.test(worksheet)) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  try { return execFileSync('python3', [xlsxConverter, worksheet], { input: bytes, stdio: ['pipe', 'pipe', 'pipe'], maxBuffer: 16 * 1024 * 1024 }); }
  catch { throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED'); }
}
export function normalizeCSV(bytes) {
  try { return execFileSync('python3', [normalizer], { input: bytes, stdio: ['pipe', 'pipe', 'pipe'], maxBuffer: 16 * 1024 * 1024 }); }
  catch { throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED'); }
}
// The digest is an integrity binding, not a signature. Only the authorized D1
// publisher can register it, after replaying the conversion with both real files.
const binding = record => JSON.stringify([record.dataVersion, record.originalFilename, record.originalSha256, record.csvSha256, record.sourceProof.method, record.sourceProof.normalizerSha256,
  ...(record.sourceProof.method === 'xlsx-sheet-v1' ? [record.sourceProof.worksheet] : [])]);
export function prepareAssociation(original, runtime, filename, version, { worksheet } = {}) {
  const xlsx = /\.xlsx$/i.test(filename);
  if ((!xlsx && worksheet !== undefined) || (xlsx && digest(normalizeXLSX(original, worksheet)) !== digest(runtime))) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  const identical = digest(original) === digest(runtime);
  if (!xlsx && !identical && digest(normalizeCSV(original)) !== digest(runtime)) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  const record = { recordVersion: 2, originalFilename: filename, originalSha256: digest(original), csvSha256: digest(runtime), dataVersion: version,
    sourceProof: xlsx ? { method: 'xlsx-sheet-v1', normalizerSha256: XLSX_CONVERTER_SHA256, worksheet } : { method: identical ? 'identity-v1' : 'csv-normalize-v1', normalizerSha256: identical ? null : NORMALIZER_SHA256 } };
  record.sourceProof.bindingSha256 = digest(binding(record));
  return record;
}
export function validateAssociation(record) {
  const p = record?.sourceProof;
  if (record?.recordVersion !== 2 || !/^[a-f0-9]{64}$/.test(record.originalSha256) || !/^[a-f0-9]{64}$/.test(record.csvSha256) ||
      !p || !['identity-v1', 'csv-normalize-v1', 'xlsx-sheet-v1'].includes(p.method) ||
      (p.method === 'xlsx-sheet-v1' && (typeof p.worksheet !== 'string' || !p.worksheet || p.worksheet.length > 31 || /[\x00-\x1f\x7f]/.test(p.worksheet) || !/\.xlsx$/i.test(record.originalFilename))) ||
      p.normalizerSha256 !== (p.method === 'identity-v1' ? null : p.method === 'xlsx-sheet-v1' ? XLSX_CONVERTER_SHA256 : NORMALIZER_SHA256) ||
      p.bindingSha256 !== digest(binding(record))) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  if (p.method === 'identity-v1' && record.originalSha256 !== record.csvSha256) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  return record;
}
export function verifyAssociation(record, original, runtime) {
  validateAssociation(record);
  if (!(original instanceof Uint8Array) || !(runtime instanceof Uint8Array) || digest(original) !== record.originalSha256 || digest(runtime) !== record.csvSha256 ||
      digest(record.sourceProof.method === 'identity-v1' ? original : record.sourceProof.method === 'xlsx-sheet-v1' ? normalizeXLSX(original, record.sourceProof.worksheet) : normalizeCSV(original)) !== record.csvSha256) throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED');
  return record;
}
export function registrationRecord(row) {
  try {
    return validateAssociation({ recordVersion: 2, originalFilename: row.original_filename, originalSha256: row.original_sha256,
      csvSha256: row.source_sha256, dataVersion: row.data_version, sourceProof: JSON.parse(row.source_proof) });
  } catch { throw new Error('SOURCE_ASSOCIATION_NOT_VERIFIED'); }
}
