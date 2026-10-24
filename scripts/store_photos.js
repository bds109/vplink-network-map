// Shared Map / Store Gallery discovery. Only a requested prefix is probed.
// No initial-load scan; opening a Viewer explicitly requests the full sequence.
const storePhotoCache = Object.create(null);
const photoProbeQueue = [];
let activePhotoProbes = 0;
function probeStorePhoto(url) {
  return new Promise((resolve, reject) => {
    photoProbeQueue.push({ url, resolve, reject });
    drainPhotoProbes();
  });
}
function drainPhotoProbes() {
  while (activePhotoProbes < 4 && photoProbeQueue.length) {
    const job = photoProbeQueue.shift();
    activePhotoProbes++;
    const image = new Image();
    let settled = false;
    const finish = (exists, error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      image.onload = image.onerror = null;
      activePhotoProbes--;
      if (error) job.reject(error); else job.resolve(exists);
      drainPhotoProbes();
    };
    const timer = setTimeout(() => finish(false, new Error('Photo request timed out')), 12000);
    image.onload = () => finish(true);
    image.onerror = async () => {
      // Image.onerror also means 403/429/network failure, not necessarily absence.
      // Only a readable 404/410 can confirm the first gap and an exact total.
      try {
        const response = await fetch(job.url, { method: 'HEAD', signal: AbortSignal.timeout(5000) });
        if (response.status === 404 || response.status === 410) finish(false);
        else finish(false, new Error('Photo availability unverified'));
      } catch (error) { finish(false, new Error('Photo availability unverified')); }
    };
    image.src = job.url;
  }
}
async function discoverStorePhotos(storeId, limit = Infinity) {
  const id = String(storeId).trim();
  if (!/^[1-9][0-9]*$/.test(id)) throw new Error('Invalid store ID');
  const entry = storePhotoCache[id] || (storePhotoCache[id] = { photos: [], complete: false, pending: null, failedAt: 0 });
  // A hover, card batch and Map carousel may request the same ID concurrently.
  while (!entry.complete && entry.photos.length < limit) {
    if (entry.failedAt && Date.now() - entry.failedAt < 30000) throw new Error('Photo availability unverified');
    if (!entry.pending) {
      const url = getStorePhotoUrl(id, entry.photos.length + 1);
      entry.pending = probeStorePhoto(url).then(exists => {
        if (exists) entry.photos.push(url); else entry.complete = true;
      }).catch(error => { entry.failedAt = Date.now(); throw error; })
        .finally(() => { entry.pending = null; });
    }
    await entry.pending;
  }
  return entry;
}
async function loadStorePhotos(data) {
  try {
    const entry = await discoverStorePhotos(data.dataset.storeid);
    data.dataset.photos = JSON.stringify(entry.photos);
    return entry;
  } catch (error) {
    // A timeout is not a missing photo and must not poison the cache.
    data.dataset.photos = JSON.stringify(storePhotoCache[data.dataset.storeid]?.photos || []);
    return null;
  }
}
