import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, readFileSync, unlinkSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepareSource, publicSource, validateSource, validateFilename, digest, publicationReceipt } from './source.mjs';
import { publishedProvenance } from './sync.mjs';
import { normalizeCSV, validateAssociation, verifyAssociation, NORMALIZER_SHA256 } from './association.mjs';
const csv = Buffer.from('isolated CSV');
const record = prepareSource(csv, csv, '门店原始上传-一.csv');
const source = publicSource(record);
test('identity provenance separately records original/final fingerprints, name and version', () => {
  assert.equal(record.originalFilename, '门店原始上传-一.csv');
  assert.equal(record.originalSha256, digest(csv)); assert.equal(record.csvSha256, digest(csv));
  assert.equal(record.sourceProof.method, 'identity-v1');
  assert.equal(source.originalFilename, undefined);
  assert.ok(!JSON.stringify(source).includes(record.originalFilename));
  assert.equal(source.csvSha256, digest(csv));
  assert.notEqual(prepareSource(csv, csv, '门店原始上传-二.csv').dataVersion, source.dataVersion);
  assert.throws(() => prepareSource(csv, Buffer.from('other'), 'a.csv'));
  for (const originalFilename of ['../a.csv', 'a\\b.csv', '', 'x\n.csv', 'a.xlsx']) assert.throws(() => validateFilename(originalFilename));
  assert.throws(() => validateSource(record, digest(csv)));
  assert.throws(() => validateSource(source, digest(Buffer.from('new CSV'))));
});
test('published metadata must match checkout, main and Production, not just CSV bytes', async () => {
  const get = async url => url.includes('map-data-source.json') ? Buffer.from(JSON.stringify(source)) : csv;
  assert.equal(await publishedProvenance(csv, source, get, async () => {}, 1), digest(csv));
  await assert.rejects(publishedProvenance(csv, { ...source, originalFilename: 'stale.csv' }, get, async () => {}, 1));
  await assert.rejects(publishedProvenance(csv, source, async url => url.includes('map-data-source') ? null : csv, async () => {}, 1));
  assert.equal(await publishedProvenance(csv, null, async url => url.includes('map-data-source') ? null : csv, async () => {}, 1), digest(csv));
  let calls = 0;
  const delayedMetadata = async url => { calls++; return url.includes('map-data-source') ? (calls <= 4 ? null : Buffer.from(JSON.stringify(source))) : csv; };
  assert.equal(await publishedProvenance(csv, source, delayedMetadata, async () => {}, 2), digest(csv));
  assert.equal(calls, 8);
});
test('two original CSV files prepare separately, keeping the stable runtime filename/bytes unchanged', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'vpl-source-cli-'));
  const cli = fileURLToPath(new URL('./source.mjs', import.meta.url));
  try {
    for (const [i, name] of ['用户提交-A.csv', '用户提交-B.csv'].entries()) {
      const bytes = Buffer.from(`ID,StoreName\n1,Synthetic ${i}\n`);
      const original = i ? Buffer.from('\uFEFF' + bytes.toString().replaceAll('\n', '\r\n')) : bytes;
      writeFileSync(path.join(dir, name), original);
      writeFileSync(path.join(dir, 'VPL门店地图信息.csv'), bytes);
      execFileSync(process.execPath, [cli, path.join(dir, name)], { cwd: dir });
      const meta = JSON.parse(readFileSync(path.join(dir, 'map-data-source.json')));
      assert.equal(meta.originalFilename, undefined); assert.equal(meta.csvSha256, digest(bytes));
      const privateRecord = JSON.parse(readFileSync(path.join(dir, '.pi/map-data-sources', meta.dataVersion + '.json')));
      assert.equal(privateRecord.originalFilename, name);
      assert.equal(privateRecord.originalSha256, digest(original)); assert.equal(privateRecord.csvSha256, digest(bytes));
      assert.equal(privateRecord.sourceProof.method, i ? 'csv-normalize-v1' : 'identity-v1');
      assert.ok(!JSON.stringify(meta).includes(name));
      assert.deepEqual(readFileSync(path.join(dir, 'VPL门店地图信息.csv')), bytes);
      assert.throws(() => execFileSync(process.execPath, [cli, path.join(dir, name)], { cwd: dir, stdio: 'pipe' }));
      unlinkSync(path.join(dir, 'map-data-source.json'));
    }
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
test('verified conversion supports differing BOM/EOL/quoting bytes without business value edits', () => {
  const original = Buffer.from('\uFEFF"ID","StoreName"\r\n"001"," 合成门店 "\r\n');
  const runtime = Buffer.from('ID,StoreName\n001, 合成门店 \n');
  assert.deepEqual(normalizeCSV(original), runtime);
  const record = prepareSource(original, runtime, '格式化前原始表.csv');
  assert.notEqual(record.originalSha256, record.csvSha256);
  assert.equal(record.sourceProof.method, 'csv-normalize-v1'); assert.equal(record.sourceProof.normalizerSha256, NORMALIZER_SHA256);
  verifyAssociation(record, original, runtime);
  assert.ok(!JSON.stringify(publicSource(record)).includes(record.originalSha256));
  for (const key of ['originalSha256', 'csvSha256', 'originalFilename', 'dataVersion']) assert.throws(() => validateAssociation({ ...record, [key]: 'tampered' }));
  assert.throws(() => validateAssociation({ ...record, sourceProof: { ...record.sourceProof, normalizerSha256: '0'.repeat(64) } }));
  assert.throws(() => verifyAssociation(record, Buffer.from('other upload'), runtime));
  for (const changed of ['ID,StoreName\n001,合成门店\n', 'ID,StoreName\n1, 合成门店 \n', 'StoreName,ID\n 合成门店 ,001\n']) assert.throws(() => prepareSource(original, Buffer.from(changed), 'unverified.csv'));
  assert.throws(() => normalizeCSV(Buffer.from('ID,Name\n1,"unclosed')));
});
test('actual publication uses exact successful Pages build, never a preparation time', async () => {
  const time = '2026-10-20T13:45:12Z';
  assert.equal(await publicationReceipt('release', async () => [{ commit: 'other', status: 'built', updated_at: time }, { commit: 'release', status: 'built', updated_at: time }]), '2026-10-20T13:45:12.000Z');
  for (const builds of [[], [{ commit: 'release', status: 'building', updated_at: time }], [{ commit: 'wrong', status: 'built', updated_at: time }]]) await assert.rejects(publicationReceipt('release', async () => builds));
});
