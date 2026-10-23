import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { basename } from 'node:path';
import { verifyAssociation, registrationRecord } from './association.mjs';
import { CSV, SOURCE, digest, publicSource, validateSource, validateFilename } from './source.mjs';
import { ACCOUNT, DATABASE } from './sync.mjs';
// Private pre-publication provenance in the existing D1, not a new service/table.
// A prepared source is never a successful publication or synchronization.
export async function registerSource(record, query, { original, runtime } = {}) {
  const marker = publicSource(record); validateFilename(record.originalFilename);
  // A caller-supplied hash/mapping JSON alone is never proof: replay against both files.
  verifyAssociation(record, original, runtime);
  const id = 'source:' + marker.dataVersion;
  const existing = (await query("SELECT * FROM map_sync_history WHERE id=? AND result='source'", [id])).results[0];
  if (existing) {
    registrationRecord(existing);
    if (existing.source_sha256 !== marker.csvSha256 || existing.original_filename !== record.originalFilename || existing.original_sha256 !== record.originalSha256 || existing.source_proof !== JSON.stringify(record.sourceProof)) throw new Error('SOURCE_REGISTRATION_CONFLICT');
    return id;
  }
  await query("INSERT INTO map_sync_history(id,started_at,original_filename,original_sha256,source_proof,source_sha256,data_version,result) VALUES (?,?,?,?,?,?,?,'source')", [id, new Date().toISOString(), record.originalFilename, record.originalSha256, JSON.stringify(record.sourceProof), marker.csvSha256, marker.dataVersion]);
  return id;
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 4 || !process.env.CLOUDFLARE_API_TOKEN) throw new Error('Requires separately approved D1 write access: register-source.mjs /private/source-record.json /actual/original.csv');
  const record = JSON.parse(readFileSync(process.argv[2], 'utf8'));
  const original = readFileSync(process.argv[3]), runtime = readFileSync(CSV);
  if (basename(process.argv[3]) !== record.originalFilename) throw new Error('SOURCE_FILENAME_MISMATCH');
  const marker = validateSource(JSON.parse(readFileSync(SOURCE, 'utf8')), digest(runtime));
  if (JSON.stringify(marker) !== JSON.stringify(publicSource(record))) throw new Error('SOURCE_METADATA_MISMATCH');
  await registerSource(record, async (sql, params) => {
    const response = await fetch(`https://api.cloudflare.com/client/v4/accounts/${ACCOUNT}/d1/database/${DATABASE}/query`, {
      method: 'POST', headers: { Authorization: `Bearer ${process.env.CLOUDFLARE_API_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql, params }), signal: AbortSignal.timeout(45000)
    });
    const value = await response.json();
    if (!response.ok || !value.success || !value.result?.[0]?.success) throw new Error('D1 registration failed/uncertain; re-read on retry, never replay blindly');
    return value.result[0];
  }, { original, runtime });
  console.log('Private source registered as unverified; publication and Gallery synchronization are NOT confirmed.');
}
