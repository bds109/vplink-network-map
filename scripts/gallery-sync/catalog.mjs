// Vendored pure planner from Gallery scripts/import-catalog.mjs; see README.
const fields = ['name', 'city', 'state', 'map_id', 'postal_code', 'address', 'latitude', 'longitude', 'store_type', 'category', 'geekbar', 'dojo', 'catalog_source', 'map_present'];
function values(store) {
  return [store.name, store.city, store.state, store.mapId, store.postalCode || '', store.address || '', store.latitude ?? null, store.longitude ?? null, store.storeType || '', store.category || '', store.geekbar || 0, store.dojo || 0, 'production', 1];
}
export function planCatalog(existing, data) {
  if (!Array.isArray(data.stores) || !data.stores.length || new Set(data.stores.map(s => s.id)).size !== data.stores.length) throw new Error('地图门店目录为空或ID重复');
  if (data.invalidRows?.length) throw new Error('正式目录存在非空无效行，拒绝部分同步');
  const current = new Map(existing.map(s => [s.id, s])); const incoming = new Set(data.stores.map(s => s.id));
  const plan = { sourceSha256: data.sourceSha256, added: [], updated: [], unchanged: [], absentFromProduction: [], isolatedLegacy: [], conflicts: [] };
  for (const store of data.stores) {
    const old = current.get(store.id);
    if (!old) { plan.added.push({ id: store.id, store }); continue; }
    const baseFields = ['name', 'city', 'state', 'map_id', 'postal_code', 'address'];
    const incomingBase = [store.name, store.city, store.state, store.mapId, store.postalCode || '', store.address || ''];
    if (old.catalog_source !== 'production' && (/^90000[123]$/.test(old.id) || old.id.startsWith('FIC-') || baseFields.some((k, i) => old[k] !== incomingBase[i]))) {
      plan.conflicts.push({ id: old.id, reason: '正式ID与测试/来源未知的旧门店冲突，禁止自动改名关联' }); continue;
    }
    const next = values(store); const changes = fields.filter((key, i) => old[key] !== next[i]);
    if (old.catalog_active !== 1) changes.push('catalog_active');
    if (changes.length) plan.updated.push({ id: store.id, fields: changes, before: Object.fromEntries(changes.map(k => [k, old[k] ?? null])), store });
    else plan.unchanged.push(store.id);
  }
  for (const old of existing) {
    if (incoming.has(old.id)) continue;
    if (old.catalog_source === 'production' && old.map_present) plan.absentFromProduction.push(old.id);
    else if (old.catalog_source !== 'production') plan.isolatedLegacy.push(old.id);
  }
  return plan;
}
export function catalogOperations(data, plan) {
  if (plan.conflicts.length) throw new Error('门店来源冲突，先人工核对变更清单，不执行同步');
  const columns = ['id', ...fields, 'source_sha256', 'catalog_active'];
  const sql = `INSERT INTO stores(${columns.join(',')}) VALUES (${columns.map(() => '?').join(',')}) ON CONFLICT(id) DO UPDATE SET ${columns.slice(1).map(c => `${c}=excluded.${c}`).join(',')}`;
  return [
    ...[...plan.added, ...plan.updated].map(({ store }) => ({ sql, params: [store.id, ...values(store), data.sourceSha256, 1] })),
    ...plan.absentFromProduction.map(id => ({ sql: "UPDATE stores SET map_present=0 WHERE id=? AND catalog_source='production'", params: [id] }))
  ];
}
