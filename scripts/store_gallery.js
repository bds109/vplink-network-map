// Runs in the existing CSV completion scope: no parallel catalog or private API.
var currentView = new URLSearchParams(location.search).get('view') === 'gallery' ? 'gallery' : 'map';
var galleryItems = [];
var gallerySearchResults = [];
var gallerySearchTimer = null;
var galleryReady = false;
var gallerySignature = null;
var galleryGeneration = 0;
var galleryCursor = 0;
var galleryChecking = false;
var galleryAutoLoadScheduled = false;
var galleryCards = new Map();
var galleryDialog = null;
var galleryScroll = 0;

function galleryElement(tag, attrs, ...children) {
  var node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(function(pair) {
    var key = pair[0], value = pair[1];
    if(key === 'class') node.className = value;
    else if(key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if(value !== false && value != null) node.setAttribute(key, String(value));
  });
  children.flat().forEach(function(child) { if(child != null) node.append(child); });
  return node;
}
function galleryButton(text, action, cls) {
  return galleryElement('button', {type:'button', class:cls || '', onClick:action}, text);
}
function galleryId(item) { return String(item.store.ID).trim(); }
function updateGalleryCount(id, entry) {
  var card = galleryCards.get(id);
  if(!card) return;
  var count = card.querySelector('.gallery-count');
  count.hidden = !entry.complete;
  count.textContent = entry.complete ? entry.photos.length + (entry.photos.length === 1 ? ' photo' : ' photos') : '';
}
function galleryCard(item, entry) {
  var id = galleryId(item), store = item.store;
  var card = galleryElement('article', {class:'store-gallery-card', 'data-store-id':id});
  var open = galleryButton('', function() { openStoreGalleryViewer(item); }, 'gallery-open');
  open.setAttribute('aria-label', 'View photos of ' + store.StoreName);
  open.append(galleryElement('img', {src:entry.photos[0], alt:'', decoding:'async'}),
    galleryElement('span', {class:'gallery-caption'},
      galleryElement('strong', {class:'gallery-name'}, store.StoreName),
      galleryElement('span', {class:'gallery-city'}, store.City || ''),
      galleryElement('span', {class:'gallery-count', hidden:true})));
  // Sibling buttons, never nested buttons: map action cannot bubble into Viewer.
  card.append(open, galleryButton('View on Map', function(event) {
    event.stopPropagation(); galleryToMap(item);
  }, 'gallery-map-button'));
  var hovering = false, second, ready = false;
  var hover = matchMedia('(min-width:768px) and (hover:hover) and (pointer:fine)');
  card.addEventListener('pointerenter', async function(event) {
    if(!hover.matches || event.pointerType === 'touch') return;
    hovering = true;
    if(ready) { card.classList.add('show-second'); return; }
    try {
      var photos = await discoverStorePhotos(id, 2);
      updateGalleryCount(id, photos);
      if(!photos.photos[1] || second) return;
      second = galleryElement('img', {class:'gallery-second', alt:'', decoding:'async'});
      second.src = photos.photos[1];
      open.insertBefore(second, open.lastChild);
      try { await second.decode(); } catch(error) { second.remove(); second = null; return; }
      ready = true;
      if(hovering && hover.matches) card.classList.add('show-second');
    } catch(error) { /* A later intentional hover can retry a timeout. */ }
  });
  card.addEventListener('pointerleave', function() { hovering = false; card.classList.remove('show-second'); });
  galleryCards.set(id, card);
  updateGalleryCount(id, entry);
  return card;
}
function syncGalleryFilters() {
  [['galleryState',getStateFilterItems(),getSelectedValues('.stateCheckbox')],
   ['galleryType',getCategoryFilterItems(),getSelectedValues('.categoryCheckbox')],
   ['galleryBrand',renderBrandFilter(),getSelectedBrands()]].forEach(function(group) {
    var select = document.getElementById(group[0]);
    select.replaceChildren(galleryElement('option', {value:''}, 'All'));
    group[1].forEach(function(item) { select.append(galleryElement('option', {value:item.value}, item.label)); });
    if(group[2].length > 1) select.append(galleryElement('option', {value:'__multiple__'}, group[2].length + ' selected'));
    select.value = group[2].length > 1 ? '__multiple__' : (group[2][0] || '');
  });
  document.getElementById('galleryBrandField').hidden = mapView.mode !== 'overview';
}
function updateStoreGallery(items) {
  galleryItems = items;
  var query = normalizeSearchText(document.getElementById('gallerySearch').value);
  // Reuse the Map search matching algorithm on the already-scoped Gallery
  // collection; never expand beyond Map filters or the current brand.
  gallerySearchResults = query ? items.filter(function(item) {
    return Number.isFinite(getSearchScore(item,query));
  }) : items;
  syncGalleryFilters();
  if(currentView !== 'gallery' || !galleryReady) return;
  // A hidden Map selection must not override a new Gallery filter on refresh.
  if(selectedStoreId && !items.some(function(item) { return galleryId(item) === selectedStoreId; })) setSelectedStore(null);
  var signature = gallerySearchResults.map(galleryId).join(',');
  if(signature === gallerySignature) {
    updateGallerySummary(); return;
  }
  gallerySignature = signature;
  galleryGeneration++;
  galleryCursor = 0;
  galleryChecking = false;
  galleryCards.clear();
  document.getElementById('galleryGrid').replaceChildren();
  document.getElementById('storeGallery').scrollTop = 0;
  updateGallerySummary();
  probeGalleryBatch();
}
function updateGallerySummary() {
  document.getElementById('gallerySummary').textContent = gallerySearchResults.length + ' matching locations · ' + galleryCards.size + ' with photos found · ' + galleryCursor + ' checked';
  var message = document.getElementById('galleryMessage');
  if(!gallerySearchResults.length) message.textContent = document.getElementById('gallerySearch').value.trim()
    ? 'No locations match this search. Try another name, city, postcode or ID.'
    : 'No matching locations. Change the shared Map filters.';
  else if(galleryChecking) message.textContent = 'Checking the next locations for store photos…';
  else if(!galleryCards.size) message.textContent = galleryCursor < gallerySearchResults.length
    ? 'Searching for store photos…' : 'No store photos found. All matching locations remain available on the Map.';
  else message.textContent = galleryCursor < gallerySearchResults.length ? 'Scroll to explore more locations.' : 'All matching locations checked. Locations without photos remain on the Map.';
}
function maybeAutoLoadGallery() {
  if(currentView !== 'gallery' || !galleryReady || galleryChecking || galleryCursor >= gallerySearchResults.length) return;
  var panel = document.getElementById('storeGallery');
  if(panel.scrollHeight - panel.scrollTop - panel.clientHeight <= 400) probeGalleryBatch();
}
function scheduleGalleryAutoLoad() {
  if(galleryAutoLoadScheduled) return;
  galleryAutoLoadScheduled = true;
  requestAnimationFrame(function() {
    galleryAutoLoadScheduled = false;
    maybeAutoLoadGallery();
  });
}
async function probeGalleryBatch() {
  if(galleryChecking || currentView !== 'gallery' || !galleryReady || galleryCursor >= gallerySearchResults.length) return;
  var generation = galleryGeneration, start = galleryCursor;
  var batch = gallerySearchResults.slice(start, start + 12);
  galleryChecking = true;
  updateGallerySummary();
  var results = new Array(batch.length), cursor = 0;
  async function worker() {
    while(cursor < batch.length && generation === galleryGeneration && currentView === 'gallery') {
      var index = cursor++;
      try { results[index] = await discoverStorePhotos(galleryId(batch[index]), 1); }
      catch(error) { results[index] = null; }
    }
  }
  await Promise.all(Array.from({length:Math.min(4,batch.length)}, worker));
  if(generation !== galleryGeneration || currentView !== 'gallery') return;
  results.forEach(function(entry, index) {
    if(entry && entry.photos.length) document.getElementById('galleryGrid').append(galleryCard(batch[index], entry));
  });
  galleryCursor = start + batch.length;
  galleryChecking = false;
  updateGallerySummary();
  if(results.some(function(entry) { return entry === null; })) {
    document.getElementById('galleryMessage').textContent = 'Some photo availability checks could not be verified. Unknown totals are not shown.';
    var retry = galleryButton('Retry photo checks', function() {
      batch.forEach(function(item) { if(storePhotoCache[galleryId(item)]) storePhotoCache[galleryId(item)].failedAt = 0; });
      gallerySignature = null; updateStoreGallery(galleryItems);
    });
    document.getElementById('galleryMessage').append(' ', retry);
  }
  scheduleGalleryAutoLoad();
}
function setStoreView(view, push) {
  var wasReady = urlStateReady;
  urlStateReady = false;
  var changed = currentView !== view;
  if(currentView === 'gallery') galleryScroll = document.getElementById('storeGallery').scrollTop;
  currentView = view;
  document.body.classList.toggle('gallery-active',view === 'gallery');
  document.getElementById('mapViewSurface').hidden = view === 'gallery';
  document.getElementById('storeGallery').hidden = view !== 'gallery';
  document.getElementById('mapViewBtn').setAttribute('aria-pressed',String(view === 'map'));
  document.getElementById('galleryViewBtn').setAttribute('aria-pressed',String(view === 'gallery'));
  if(view === 'gallery') {
    suppressPopupSelection = true; map.closePopup(); suppressPopupSelection = false;
    updateStoreGallery(galleryItems);
    document.getElementById('storeGallery').scrollTop = galleryScroll;
    scheduleGalleryAutoLoad();
  } else {
    // Invalidate after display is restored, before positioning an ID target.
    map.invalidateSize({pan:false});
    if(changed) { galleryGeneration++; galleryChecking = false; }
    if(changed && push && selectedStoreId) {
      var selected = findScopedStore(selectedStoreId);
      if(selected) focusSearchTarget(selected);
    }
  }
  urlStateReady = wasReady;
  if(push && changed && urlStateReady) {
    var url = shareUrl(); history.pushState(null,'',url.pathname + url.search + url.hash);
  }
  if(urlStateReady) syncUrlState();
}
function openGalleryMapTab(item) {
  if(item && !pageScopeMarkers.includes(item)) return;
  // Keep current Preview route and filters; leave original Gallery tab and
  // photo viewer unchanged.
  var url = shareUrl();
  url.searchParams.delete('view');
  if(item) url.searchParams.set('id',galleryId(item));
  window.open(url.href,'_blank','noopener,noreferrer');
}
function galleryToMap(item) {
  openGalleryMapTab(item);
}
function openStoreGalleryViewer(item) {
  if(galleryDialog || !pageScopeMarkers.includes(item)) return;
  var trigger = document.activeElement, id = galleryId(item), store = item.store;
  var entry = storePhotoCache[id], index = 0, start;
  var image = galleryElement('img', {class:'viewer-image', alt:store.StoreName});
  var counter = galleryElement('span', {class:'viewer-counter', 'aria-live':'polite'});
  var close = galleryButton('×', function() { dialog.close(); }, 'viewer-close');
  close.setAttribute('aria-label','Close viewer');
  var previous = galleryButton('‹',function() { change(-1); },'previous');
  previous.setAttribute('aria-label','Previous photo');
  var next = galleryButton('›',function() { change(1); },'next');
  next.setAttribute('aria-label','Next photo');
  var stage = galleryElement('div',{class:'viewer-stage'},image,previous,next);
  var strip = galleryElement('nav',{class:'viewer-thumbnails','aria-label':'Store photos'});
  var status = galleryElement('span',{},'Loading photos…');
  var mapButton = galleryButton('View on Map',function(event) { event.stopPropagation(); galleryToMap(item); },'viewer-map');
  var dialog = galleryElement('dialog',{class:'store-gallery-viewer','aria-label':store.StoreName + ' photos'},
    galleryElement('div',{class:'viewer'},
      galleryElement('div',{class:'viewer-top'},
        galleryElement('div',{class:'viewer-heading'},galleryElement('h2',{},store.StoreName),galleryElement('p',{},store.City || '')),
        galleryElement('div',{class:'viewer-actions'},counter,close)),stage,
      galleryElement('div',{class:'viewer-footer'},strip,
        galleryElement('div',{class:'viewer-context'},status,mapButton))));
  var thumbs = [];
  function change(delta) { index = (index + delta + entry.photos.length) % entry.photos.length; render(); }
  function render() {
    image.src = entry.photos[index]; image.alt = store.StoreName + ' · photo ' + (index + 1);
    counter.textContent = (index + 1) + ' / ' + (entry.complete ? entry.photos.length : '…');
    previous.hidden = next.hidden = entry.photos.length < 2;
    while(thumbs.length < entry.photos.length) {
      var i = thumbs.length;
      var thumb = galleryButton('',(function(n) { return function() { index = n; render(); }; })(i),'viewer-thumb');
      thumb.setAttribute('aria-label','View photo ' + (i + 1));
      thumb.append(galleryElement('img',{src:entry.photos[i],alt:'',loading:'lazy',decoding:'async'}));
      thumbs.push(thumb); strip.append(thumb);
    }
    thumbs.forEach(function(thumb,i) { thumb.setAttribute('aria-pressed',String(i === index)); });
    if(dialog.open && thumbs[index]) strip.scrollTo({left:Math.max(0,thumbs[index].offsetLeft-strip.clientWidth/2+thumbs[index].clientWidth/2),behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth'});
    status.textContent = (stateNameMap[store.State] || store.State || '') + (entry.complete ? ' · Store photos' : ' · Checking remaining photos…');
  }
  async function discover() {
    try {
      while(dialog.open && !entry.complete) {
        entry = await discoverStorePhotos(id,entry.photos.length+1);
        if(dialog.open) render();
      }
      updateGalleryCount(id,entry);
    } catch(error) {
      if(!dialog.open) return;
      status.replaceChildren(entry.photos.length + ' photos loaded · total unverified. ',galleryButton('Retry',function() { entry.failedAt=0; discover(); }));
    }
  }
  stage.addEventListener('touchstart',function(event) { start = {x:event.changedTouches[0].clientX,y:event.changedTouches[0].clientY}; },{passive:true});
  stage.addEventListener('touchend',function(event) {
    if(!start) return;
    var dx=event.changedTouches[0].clientX-start.x, dy=event.changedTouches[0].clientY-start.y;
    if(Math.abs(dx)>45 && Math.abs(dx)>Math.abs(dy)*1.5) change(dx<0?1:-1);
    start=null;
  },{passive:true});
  dialog.addEventListener('keydown',function(event) {
    if(event.key==='ArrowRight'||event.key==='ArrowLeft') { event.preventDefault(); change(event.key==='ArrowRight'?1:-1); }
  });
  dialog.addEventListener('close',function() {
    dialog.remove(); galleryDialog=null;
    if(currentView==='gallery' && trigger && trigger.isConnected) trigger.focus({preventScroll:true});
  },{once:true});
  document.body.append(dialog); galleryDialog=dialog; render(); dialog.showModal(); close.focus(); discover();
}
function restoreStoreViewHistory() {
  if(galleryDialog) galleryDialog.close();
  var params=new URLSearchParams(location.search);
  urlStateReady=false;
  galleryGeneration++; galleryChecking=false;
  currentView=params.get('view')==='gallery'?'gallery':'map';
  suppressPopupSelection=true; map.closePopup(); suppressPopupSelection=false;
  selectedStoreId=null;
  [['state','.stateCheckbox'],['type','.categoryCheckbox'],['brand','.brandCheckbox']].forEach(function(group) {
    if(group[0]==='brand' && mapView.mode!=='overview') return;
    document.querySelectorAll(group[1]).forEach(function(cb) { cb.checked=params.getAll(group[0]).includes(cb.value); });
  });
  activeArea=parseAreaBounds(params.get('bbox')); areaPrompt=false;
  applyFilters();
  var item=findScopedStore(params.get('id'));
  if(item) { activeArea=null; adjustFiltersForSearchTarget(item); applyFilters(); setSelectedStore(galleryId(item)); }
  restoreMapView(params);
  setStoreView(params.get('view')==='gallery'?'gallery':'map',false);
  if(item && currentView==='map') { map.setView(item.marker.getLatLng(),16,{animate:false}); focusSearchTarget(item); }
  urlStateReady=true; syncUrlState();
}
function initializeStoreGallery() {
  var label=mapView.mode==='brand'? 'VPLINK × '+mapView.brand.label.toUpperCase():'VPLINK';
  document.getElementById('viewBrand').textContent=label;
  var scopeLabel=document.getElementById('galleryBrandTitle');
  scopeLabel.textContent=mapView.mode==='brand'?mapView.brand.label.toUpperCase():'';
  scopeLabel.hidden=mapView.mode!=='brand';
  var performance=document.getElementById('performanceGalleryLink');
  var scope=mapView.mode==='overview' ? 'overview' : (mapView.mode==='brand' ? mapView.brand.slug : null);
  var config=scope && STORE_GALLERY_CONFIG.performanceGallery[scope];
  // No Performance tab for the public neutral map; internal routes expose
  // only their own already-password-protected Performance destination.
  var enabled=!!(config && config.url && config.status==='password-protected' &&
    config.url.startsWith('https://gallery.vpl-gmbh.com/'));
  performance.hidden=!enabled;
  if(enabled) {
    performance.href=config.url;
    performance.removeAttribute('aria-disabled');
    performance.removeAttribute('tabindex');
    performance.title='Open Performance sign-in in a new tab';
  }
  [['galleryState','.stateCheckbox'],['galleryType','.categoryCheckbox'],['galleryBrand','.brandCheckbox']].forEach(function(group) {
    document.getElementById(group[0]).addEventListener('change',function(event) {
      if(event.target.value==='__multiple__') return;
      replaceFilterDimension(group[1],event.target.value); applyFilters();
    });
  });
  document.getElementById('mapViewBtn').addEventListener('click',function() { setStoreView('map',true); });
  document.getElementById('galleryViewBtn').addEventListener('click',function() { setStoreView('gallery',true); });
  document.getElementById('gallerySearch').addEventListener('input',function() {
    clearTimeout(gallerySearchTimer);
    gallerySearchTimer = setTimeout(function() {
      updateStoreGallery(galleryItems);
    },160);
  });
  document.getElementById('storeGallery').addEventListener('scroll',scheduleGalleryAutoLoad,{passive:true});
  window.addEventListener('popstate',restoreStoreViewHistory);
  setStoreView(currentView,false);
}
