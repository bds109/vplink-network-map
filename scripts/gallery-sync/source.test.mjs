import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, readFileSync, unlinkSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepareSource, publicSource, validateSource, validateFilename, digest, publicationReceipt } from './source.mjs';
import { publishedProvenance } from './sync.mjs';
import { normalizeCSV, normalizeXLSX, validateAssociation, verifyAssociation, NORMALIZER_SHA256, XLSX_CONVERTER_SHA256 } from './association.mjs';
import { registerSource } from './register-source.mjs';
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
  for (const originalFilename of ['../a.csv', 'a\\b.csv', '', 'x\n.csv', 'a.xls']) assert.throws(() => validateFilename(originalFilename));
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
// Synthetic OOXML only; real approved workbook is replayed privately at release time.
function workbook({ formula = false, badType = false } = {}) {
  return execFileSync('python3', ['-c', `
import io,sys,zipfile,json
x=json.load(sys.stdin); b=io.BytesIO()
with zipfile.ZipFile(b,'w') as z:
 z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Selected" r:id="r1"/><sheet name="Other" r:id="r2"/></sheets></workbook>')
 z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Type="office/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Type="office/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
 row='<row r="1">'+''.join('<c r="'+c+'1" t="inlineStr"><is><t>'+v+'</t></is></c>' for c,v in zip('ABCDE',['ID','StoreName','Latitude','Longitude','Note']))+'</row>'
 row+='<row r="2"><c r="A2"><v>001</v></c><c r="B2" t="inlineStr"><is><t> Synthetic, 店 </t></is></c><c r="C2">'+('<f>1+1</f>' if x['formula'] else '')+'<v>52.123456789</v></c><c r="D2"><v>13.50000000</v></c><c r="E2"'+(' t="e"' if x['badType'] else '')+'><v></v></c></row><row r="3"><c r="A3"/></row>'
 z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+row+'</sheetData></worksheet>')
 z.writestr('xl/worksheets/sheet2.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>')
sys.stdout.buffer.write(b.getvalue())
`], { input: JSON.stringify({ formula, badType }) });
}
test('xlsx-sheet-v1 replays only the explicit worksheet and binds converter, sheet and both fingerprints', () => {
  const original = workbook();
  const runtime = Buffer.from('ID,StoreName,Latitude,Longitude,Note\n001," Synthetic, 店 ",52.12345679,13.5,\n,,,,\n');
  assert.deepEqual(normalizeXLSX(original, 'Selected'), runtime);
  const record = prepareSource(original, runtime, 'synthetic.xlsx', { worksheet: 'Selected' });
  assert.equal(record.sourceProof.method, 'xlsx-sheet-v1');
  assert.equal(record.sourceProof.normalizerSha256, XLSX_CONVERTER_SHA256);
  assert.equal(record.sourceProof.worksheet, 'Selected');
  verifyAssociation(record, original, runtime);
  assert.deepEqual(Object.keys(publicSource(record)).sort(), ['csvSha256', 'dataVersion', 'schemaVersion']);
  for (const sheet of [undefined, '', 'Missing', 'Other']) assert.throws(() => prepareSource(original, runtime, 'synthetic.xlsx', { worksheet: sheet }));
  assert.throws(() => prepareSource(original, Buffer.from(runtime.toString().replace('001', '1')), 'synthetic.xlsx', { worksheet: 'Selected' }));
  assert.throws(() => prepareSource(original, original, 'synthetic.xlsx'));
  assert.throws(() => prepareSource(runtime, runtime, 'synthetic.csv', { worksheet: 'Selected' }));
  for (const key of ['worksheet', 'normalizerSha256', 'bindingSha256', 'method']) assert.throws(() => validateAssociation({ ...record, sourceProof: { ...record.sourceProof, [key]: 'tampered' } }));
  assert.throws(() => verifyAssociation(record, Buffer.concat([original, Buffer.from('changed')]), runtime));
  for (const invalid of [workbook({ formula: true }), workbook({ badType: true }), Buffer.from('not a ZIP')]) assert.throws(() => normalizeXLSX(invalid, 'Selected'));
});
test('XLSX private registration requires real files, is immutable/idempotent and does not write catalog', async () => {
  const original = workbook(), runtime = normalizeXLSX(original, 'Selected');
  const record = prepareSource(original, runtime, 'synthetic.xlsx', { worksheet: 'Selected' });
  let row, inserts = 0;
  const query = async (sql, params) => {
    assert.ok(sql.includes('map_sync_history')); assert.ok(!sql.includes('stores'));
    if (sql.startsWith('SELECT')) return { results: row ? [row] : [] };
    inserts++;
    row = { id: params[0], original_filename: params[2], original_sha256: params[3], source_proof: params[4], source_sha256: params[5], data_version: params[6] };
    return { results: [] };
  };
  await assert.rejects(registerSource(record, query));
  const files = { original, runtime };
  const id = await registerSource(record, query, files);
  assert.equal(await registerSource(record, query, files), id); assert.equal(inserts, 1);
  const conflicting = { ...prepareSource(original, runtime, 'other.xlsx', { worksheet: 'Selected' }), dataVersion: record.dataVersion };
  // Produce a valid conflicting proof for the same version (not just a broken digest).
  const { prepareAssociation } = await import('./association.mjs');
  Object.assign(conflicting, prepareAssociation(original, runtime, 'other.xlsx', record.dataVersion, { worksheet: 'Selected' }));
  await assert.rejects(registerSource(conflicting, query, files), /SOURCE_REGISTRATION_CONFLICT/);
  assert.equal(inserts, 1);
});
test('legacy CSV binding bytes remain unchanged', () => {
  for (const original of [Buffer.from('ID\n1\n'), Buffer.from('\uFEFF"ID"\r\n"1"\r\n')]) {
    const record = prepareSource(original, normalizeCSV(original), 'legacy.csv');
    const p = record.sourceProof;
    assert.equal(p.bindingSha256, digest(JSON.stringify([record.dataVersion, record.originalFilename, record.originalSha256, record.csvSha256, p.method, p.normalizerSha256])));
    verifyAssociation(record, original, normalizeCSV(original));
  }
});
test('actual publication uses exact successful Pages build, never a preparation time', async () => {
  const time = '2026-10-20T13:45:12Z';
  assert.equal(await publicationReceipt('release', async () => [{ commit: 'other', status: 'built', updated_at: time }, { commit: 'release', status: 'built', updated_at: time }]), '2026-10-20T13:45:12.000Z');
  for (const builds of [[], [{ commit: 'release', status: 'building', updated_at: time }], [{ commit: 'wrong', status: 'built', updated_at: time }]]) await assert.rejects(publicationReceipt('release', async () => builds));
});
