import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "map_template.html"
BRAND_CONFIG_SOURCE = ROOT / "scripts" / "brand_config.json"
CANDIDATE_CSV = ROOT / "VPL门店地图信息.csv"
PREVIEW_DIR = ROOT / "preview"
PREVIEW_DATA = PREVIEW_DIR / "data" / "locations.csv"
PREVIEW_DATA_HASH = PREVIEW_DIR / "data" / "locations.sha256"

PREVIEW_META = '<meta name="robots" content="noindex,nofollow">'
PREVIEW_BADGE = """<div id="previewEnvBadge">
PREVIEW ENVIRONMENT
</div>
"""
SEARCH_MARKUP = """<div id="searchControl">
<label class="search-input-wrap" for="locationSearch">
<span class="search-icon" aria-hidden="true">⌕</span>
<input id="locationSearch" type="search" inputmode="search" autocomplete="off" placeholder="Search locations…" aria-label="Search locations" aria-controls="searchResults" aria-expanded="false">
</label>
<div id="showingCount" aria-live="polite">Showing 0 of 0 locations</div>
<div id="searchResults" role="listbox" aria-label="Location search results" hidden></div>
</div>
"""
PREVIEW_CSS = """
#previewEnvBadge{
position:fixed;
top:14px;
right:14px;
z-index:1000001;
padding:10px 14px;
border-radius:999px;
background:#F97316;
color:#ffffff;
font-size:12px;
font-weight:800;
letter-spacing:.6px;
box-shadow:0 10px 30px rgba(249,115,22,.35);
pointer-events:none;
}

#mapTitle.is-brand-title{
display:flex;
flex-direction:column;
align-items:center;
justify-content:center;
height:36px;
padding-right:30px;
line-height:1.1;
white-space:nowrap;
}

#mapTitle.is-brand-title .map-title-main{
font-size:12px;
font-weight:900;
letter-spacing:.5px;
}

#mapTitle.is-brand-title .map-title-subtitle{
margin-top:2px;
font-size:9px;
font-weight:800;
letter-spacing:1.2px;
}

#mapFloatingTitle.is-brand-title{
width:min(780px,calc(100vw - 420px));
}

#mapFloatingTitle.is-brand-title #mapFloatingTitleText,
#mapFloatingTitle.is-brand-title #mapFloatingTitleFallback{
font-size:clamp(18px,1.8vw,36px);
letter-spacing:.01em;
}

#searchControl{
position:absolute;
top:20px;
left:20px;
z-index:10002;
width:min(240px,calc(100vw - 40px));
box-sizing:border-box;
}

.search-input-wrap{
display:flex;
align-items:center;
box-sizing:border-box;
height:38px;
padding:0 10px;
border:1px solid rgba(255,255,255,.95);
border-radius:10px;
background:rgba(255,255,255,.76);
backdrop-filter:blur(30px);
-webkit-backdrop-filter:blur(30px);
box-shadow:0 8px 24px rgba(15,23,42,.10);
}

.search-icon{
margin-right:7px;
color:#475569;
font-size:18px;
line-height:1;
}

#locationSearch{
width:100%;
min-width:0;
border:0;
outline:0;
background:transparent;
color:#0F172A;
font:inherit;
font-size:13px;
}

#locationSearch::placeholder{
color:#64748B;
}

#showingCount{
margin-top:4px;
padding:2px 8px;
border-radius:6px;
background:rgba(255,255,255,.68);
color:#334155;
font-size:11px;
font-weight:700;
line-height:18px;
box-shadow:0 4px 14px rgba(15,23,42,.06);
}

#searchResults{
position:absolute;
top:64px;
left:0;
right:0;
max-height:320px;
overflow-y:auto;
overflow-x:hidden;
box-sizing:border-box;
padding:5px;
border:1px solid rgba(255,255,255,.95);
border-radius:10px;
background:rgba(255,255,255,.94);
backdrop-filter:blur(30px);
-webkit-backdrop-filter:blur(30px);
box-shadow:0 12px 32px rgba(15,23,42,.16);
}

.search-result-status{
padding:8px;
color:#475569;
font-size:12px;
font-weight:700;
}

.search-result-button{
display:block;
width:100%;
box-sizing:border-box;
padding:7px 8px;
border:0;
border-radius:6px;
background:transparent;
text-align:left;
cursor:pointer;
}

.search-result-button:hover,
.search-result-button:focus-visible{
background:#EFF6FF;
outline:2px solid #2563EB;
outline-offset:-2px;
}

.search-result-name{
display:block;
overflow:hidden;
color:#0F172A;
font-size:13px;
font-weight:800;
text-overflow:ellipsis;
white-space:nowrap;
}

.search-result-meta{
display:block;
margin-top:2px;
overflow:hidden;
color:#64748B;
font-size:11px;
text-overflow:ellipsis;
white-space:nowrap;
}

#filter-panel{
top:100px;
max-height:calc(100vh - 120px);
overflow-y:auto;
overflow-x:hidden;
}

#openFilterBtn{
top:100px;
}

#clearAllFilters{
display:none;
width:100%;
min-height:28px;
padding:4px 8px;
border:1px solid #CBD5E1;
border-radius:6px;
background:rgba(255,255,255,.28);
color:#334155;
font:inherit;
font-size:12px;
font-weight:700;
cursor:pointer;
}

.filter-sections{
display:flex;
flex-direction:column;
gap:8px;
width:100%;
box-sizing:border-box;
}

.filter-section{
width:100%;
box-sizing:border-box;
padding-top:8px;
border-top:1px solid rgba(255,255,255,.35);
}

.filter-section:first-child{
padding-top:0;
border-top:none;
}

.filter-section-header{
display:flex;
align-items:center;
justify-content:space-between;
gap:6px;
min-width:0;
margin-bottom:5px;
}

.filter-section-title{
min-width:0;
font-size:14px;
font-weight:700;
color:#0F172A;
white-space:nowrap;
}

.selection-summary{
font-size:11px;
font-weight:600;
color:#475569;
}

#stateFilter,
#categoryFilter,
#brandFilter{
width:100%;
max-width:100%;
max-height:none;
box-sizing:border-box;
overflow:hidden;
}

.filter-list.is-compact .filter-item:nth-child(n+5):not(.is-selected){
display:none;
}

.filter-list.is-expanded{
max-height:260px !important;
overflow-y:auto !important;
overflow-x:hidden;
}

.filter-expand-button{
width:100%;
min-height:24px;
margin-top:4px;
padding:2px 6px;
border:1px solid rgba(148,163,184,.55);
border-radius:5px;
background:rgba(255,255,255,.18);
color:#334155;
font:inherit;
font-size:12px;
font-weight:700;
cursor:pointer;
}

.filter-expand-button:hover{
background:rgba(255,255,255,.5);
}

.filter-option[aria-disabled="true"]{
cursor:default;
}

.filter-section[hidden]{
display:none;
}

@media (max-width: 768px){
#searchControl{
top:10px;
left:10px;
width:calc(100vw - 130px);
min-width:180px;
}

#searchResults{
max-height:32vh;
}

#filter-panel{
display:none;
top:124px;
left:10px;
width:min(280px,calc(100vw - 20px));
max-height:calc(100vh - 134px);
}

#openFilterBtn{
display:block;
top:80px;
left:10px;
padding:8px 12px;
}

#clearAllFilters{
display:block;
}

#mapTitle.is-brand-title{
padding-right:40px;
}

#mapTitle.is-brand-title .map-title-main{
font-size:10px;
}

.filter-list.is-expanded{
max-height:32vh !important;
}

#previewEnvBadge{
top:80px;
right:10px;
font-size:10px;
padding:7px 10px;
}
}
"""

FILTER_MARKUP = """
<div id="filterSections" class="filter-sections" aria-label="Map filters">
<section id="stateFilterContainer" class="filter-section" data-filter-section="states" aria-labelledby="stateFilterHeading">
<div class="filter-section-header">
<div id="stateFilterHeading" class="filter-section-title">States<span id="stateSelectionSummary" class="selection-summary"></span></div>
<button id="clearStateFilter" type="button">Clear</button>
</div>
<div id="stateFilter" class="filter-list is-compact"></div>
<button id="toggleStateFilter" class="filter-expand-button" type="button" hidden>Show all</button>
</section>

<section id="categoryFilterContainer" class="filter-section" data-filter-section="categories" aria-labelledby="categoryFilterHeading">
<div class="filter-section-header">
<div id="categoryFilterHeading" class="filter-section-title">Categories<span id="categorySelectionSummary" class="selection-summary"></span></div>
<button id="clearCategoryFilter" type="button">Clear</button>
</div>
<div id="categoryFilter" class="filter-list is-compact"></div>
<button id="toggleCategoryFilter" class="filter-expand-button" type="button" hidden>Show all</button>
</section>

<section id="brandFilterContainer" class="filter-section" data-filter-section="brands" aria-labelledby="brandFilterHeading">
<div class="filter-section-header">
<div id="brandFilterHeading" class="filter-section-title">Brand<span id="brandSelectionSummary" class="selection-summary"></span></div>
<button id="clearBrandFilter" type="button">All</button>
</div>
<div id="brandFilter" class="filter-list is-compact"></div>
<button id="toggleBrandFilter" class="filter-expand-button" type="button" hidden>Show all</button>
</section>
<button id="clearAllFilters" type="button">Clear filters</button>
</div>"""

FILTER_LOGIC = """
var FILTER_GROUPS = [
{key:'states',inputClass:'stateCheckbox',rowClass:'state-item',containerId:'stateFilter',sectionId:'stateFilterContainer',summaryId:'stateSelectionSummary',toggleId:'toggleStateFilter'},
{key:'categories',inputClass:'categoryCheckbox',rowClass:'category-item',containerId:'categoryFilter',sectionId:'categoryFilterContainer',summaryId:'categorySelectionSummary',toggleId:'toggleCategoryFilter'},
{key:'brands',inputClass:'brandCheckbox',rowClass:'brand-item',containerId:'brandFilter',sectionId:'brandFilterContainer',summaryId:'brandSelectionSummary',toggleId:'toggleBrandFilter'}
];

var expandedFilterSection = null;
var pageScopeMarkers = [];
var mobileFiltersOpen = false;
var searchResultItems = [];

function applyViewTitle(){
if(mapView.mode !== 'brand' || !mapView.brand){
return;
}

var brandName = mapView.brand.label.toUpperCase();
var panelTitle = document.getElementById('mapTitle');
var floatingTitle = 'VPLINK × ' + brandName + ' NETWORK MAP';
var panelMain = document.createElement('span');
var panelSubtitle = document.createElement('span');

panelMain.className = 'map-title-main';
panelMain.textContent = 'VPLINK × ' + brandName;
panelSubtitle.className = 'map-title-subtitle';
panelSubtitle.textContent = 'NETWORK MAP';
panelTitle.textContent = '';
panelTitle.appendChild(panelMain);
panelTitle.appendChild(panelSubtitle);
panelTitle.classList.add('is-brand-title');

document.title = 'VPLINK × ' + mapView.brand.label + ' Network Map';
document.getElementById('mapFloatingTitle').setAttribute('aria-label',floatingTitle);
document.getElementById('mapFloatingTitle').classList.add('is-brand-title');
document.getElementById('mapFloatingTitleTextBase').textContent = floatingTitle;
document.getElementById('mapFloatingTitleTextShine').textContent = floatingTitle;
document.getElementById('mapFloatingTitleFallback').textContent = floatingTitle;
document.getElementById('clearBrandFilter').hidden = true;
}

function getSelectedValues(selector){
return Array.prototype.map.call(
document.querySelectorAll(selector + ':checked'),
function(cb){ return cb.value; }
);
}

function getSelectedBrands(){
return getSelectedValues('.brandCheckbox');
}

function getFilterSelections(){
return {
states:getSelectedValues('.stateCheckbox'),
categories:getSelectedValues('.categoryCheckbox'),
brands:getSelectedBrands()
};
}

function sortFilterItems(items,selectedValues){
return items.slice().sort(function(a,b){
var selectedDifference = Number(selectedValues.includes(b.value)) - Number(selectedValues.includes(a.value));
return selectedDifference || a.label.localeCompare(b.label);
});
}

function getStateFilterItems(){
return Object.keys(stateCount).map(function(state){
return {value:state,label:state,count:stateCount[state]};
});
}

function getCategoryFilterItems(){
return Object.keys(categoryCount).map(function(category){
return {value:category,label:category,count:categoryCount[category]};
});
}

function renderBrandFilter(){
if(mapView.mode === 'neutral'){
return [];
}
var visibleBrands = mapView.mode === 'brand' ? [mapView.brand] : BRAND_CONFIG;
return visibleBrands.filter(Boolean).map(function(brand){
return {
value:brand.slug,
label:brand.label,
count:allMarkers.filter(function(item){ return item.store[brand.column] === '1'; }).length
};
});
}

function itemMatchesBrand(item,brand){
return Boolean(brand && item.store[brand.column] === '1');
}

function getPageScopeMarkers(){
if(mapView.mode !== 'brand' || !mapView.brand){
return allMarkers.slice();
}
return allMarkers.filter(function(item){
return itemMatchesBrand(item,mapView.brand);
});
}

function rebuildFacetCounts(items){
stateCount = {};
categoryCount = {};
items.forEach(function(item){
var state = stateNameMap[item.store.State];
var category = item.store.StoreType;
if(state){
stateCount[state] = (stateCount[state] || 0) + 1;
}
if(category){
categoryCount[category] = (categoryCount[category] || 0) + 1;
}
});
}

function filterItemsForGroup(group){
if(group.key === 'states'){
return getStateFilterItems();
}
if(group.key === 'categories'){
return getCategoryFilterItems();
}
return renderBrandFilter();
}

function updateFilterSection(group,selectedValues){
var container = document.getElementById(group.containerId);
var summary = document.getElementById(group.summaryId);
var toggle = document.getElementById(group.toggleId);
var total = container.querySelectorAll('.filter-item').length;
var expanded = expandedFilterSection === group.key;
var isClientBrand = group.key === 'brands' && mapView.mode === 'brand';

summary.hidden = isClientBrand;
summary.textContent = isClientBrand ? '' : (selectedValues.length ? ' · ' + selectedValues.length + ' selected' : '');
toggle.hidden = total <= 4;
toggle.textContent = expanded ? 'Show less' : 'Show all';
container.classList.toggle('is-compact',!expanded);
container.classList.toggle('is-expanded',expanded);
}

function updateFilterSectionPresentation(selections){
FILTER_GROUPS.forEach(function(group){
var section = document.getElementById(group.sectionId);
if(group.key === 'brands' && mapView.mode === 'neutral'){
section.hidden = true;
return;
}
section.hidden = false;
updateFilterSection(group,selections[group.key]);
});
}

function renderFilterSection(group,items,selectedValues){
var container = document.getElementById(group.containerId);
container.innerHTML = '';
sortFilterItems(items,selectedValues).forEach(function(item){
var selected = selectedValues.includes(item.value);
var isFixedBrand = group.key === 'brands' && mapView.mode === 'brand';
var row = document.createElement('div');
row.className = group.rowClass + ' filter-item' + (selected ? ' is-selected' : '');
row.innerHTML =
'<label class="filter-chip filter-option" tabindex="' + (isFixedBrand ? '-1' : '0') + '" role="checkbox" aria-checked="' + selected + '" aria-disabled="' + isFixedBrand + '">' +
'<input type="checkbox" class="' + group.inputClass + '" value="' + item.value + '">' +
'<span class="chip-name">' + item.label + '</span>' +
'<span class="chip-count">' + item.count + '</span>' +
'</label>';
row.querySelector('input').checked = selected;
row.querySelector('input').disabled = isFixedBrand;
container.appendChild(row);
});
}

function restoreFilterFocus(focusTarget){
if(!focusTarget){
return;
}
var target;
if(focusTarget.controlId){
target = document.getElementById(focusTarget.controlId);
}else if(focusTarget.inputClass){
var input = document.querySelector('.' + focusTarget.inputClass + '[value="' + focusTarget.value + '"]');
target = input && input.closest('.filter-option');
}
if(target){
target.focus();
}
}

function renderFilterSections(selections,focusTarget){
FILTER_GROUPS.forEach(function(group){
renderFilterSection(group,filterItemsForGroup(group),selections[group.key]);
});
updateFilterSectionPresentation(selections);
restoreFilterFocus(focusTarget);
}

function ensureAutoExpansion(selections,preferredGroup){
if(preferredGroup && selections[preferredGroup].length > 4){
expandedFilterSection = preferredGroup;
return;
}
if(expandedFilterSection){
return;
}
var group = FILTER_GROUPS.find(function(candidate){
return (candidate.key !== 'brands' || mapView.mode !== 'neutral') && selections[candidate.key].length > 4;
});
if(group){
expandedFilterSection = group.key;
}
}

function toggleFilterExpansion(groupKey){
expandedFilterSection = expandedFilterSection === groupKey ? null : groupKey;
updateFilterSectionPresentation(getFilterSelections());
document.getElementById(FILTER_GROUPS.find(function(group){ return group.key === groupKey; }).toggleId).focus();
}

function updateStats(filteredMarkers){
var states = [];
var categories = [];

filteredMarkers.forEach(function(item){
var state = stateNameMap[item.store.State];
var category = item.store.StoreType;

if(state && !states.includes(state)){
states.push(state);
}

if(category && !categories.includes(category)){
categories.push(category);
}
});

document.getElementById('storeCount').innerHTML = filteredMarkers.length;
document.getElementById('counterLocations').innerHTML = filteredMarkers.length + ' Locations';
document.getElementById('counterStates').innerHTML = states.length + ' States';
document.getElementById('counterCategories').innerHTML = categories.length + ' Categories';
document.getElementById('stateCountDisplay').innerHTML = states.length;
document.getElementById('categoryCountDisplay').innerHTML = categories.length;
var scopeTotal = pageScopeMarkers && pageScopeMarkers.length ? pageScopeMarkers.length : filteredMarkers.length;
document.getElementById('showingCount').textContent =
'Showing ' + filteredMarkers.length + ' of ' + scopeTotal + ' locations';
}

function getActiveFilterDimensionCount(selections){
var count = 0;
if(selections.states.length){ count++; }
if(selections.categories.length){ count++; }
if(mapView.mode === 'overview' && selections.brands.length){ count++; }
return count;
}

function updateMobileFilterButton(selections){
var count = getActiveFilterDimensionCount(selections);
var button = document.getElementById('openFilterBtn');
button.textContent = isMobileFiltersLayout() ? (count ? 'Filters (' + count + ')' : 'Filters') : '☰ Filters';
button.setAttribute('aria-label',button.textContent);
}

function applyFilters(focusTarget){
var selections = getFilterSelections();
ensureAutoExpansion(selections,focusTarget && focusTarget.group);

var filteredMarkers = pageScopeMarkers.filter(function(item){
var state = stateNameMap[item.store.State];
var category = item.store.StoreType;
var stateMatch = selections.states.length === 0 || selections.states.includes(state);
var categoryMatch = selections.categories.length === 0 || selections.categories.includes(category);
var brandMatch = mapView.mode !== 'overview' || selections.brands.length === 0 || selections.brands.some(function(slug){
var brand = BRAND_CONFIG.find(function(candidate){ return candidate.slug === slug; });
return itemMatchesBrand(item,brand);
});
return stateMatch && categoryMatch && brandMatch;
});

window.renderMarkers(filteredMarkers);
updateStats(filteredMarkers);
renderFilterSections(selections,focusTarget);
updateMobileFilterButton(selections);
return filteredMarkers;
}

function clearFilter(groupKey,controlId){
var group = FILTER_GROUPS.find(function(candidate){ return candidate.key === groupKey; });
document.querySelectorAll('.' + group.inputClass).forEach(function(cb){ cb.checked = false; });
applyFilters({group:groupKey,controlId:controlId});
}

document.getElementById('clearStateFilter').addEventListener('click',function(){
clearFilter('states','clearStateFilter');
});

document.getElementById('clearCategoryFilter').addEventListener('click',function(){
clearFilter('categories','clearCategoryFilter');
});

document.getElementById('clearBrandFilter').addEventListener('click',function(){
clearFilter('brands','clearBrandFilter');
});

function clearAllUserFilters(){
document.querySelectorAll('.stateCheckbox,.categoryCheckbox').forEach(function(cb){
cb.checked = false;
});
if(mapView.mode === 'overview'){
document.querySelectorAll('.brandCheckbox').forEach(function(cb){ cb.checked = false; });
}
applyFilters({controlId:'clearAllFilters'});
}

document.getElementById('clearAllFilters').addEventListener('click',clearAllUserFilters);

document.getElementById('filterSections').addEventListener('click',function(e){
var toggle = e.target.closest('.filter-expand-button');
if(!toggle || toggle.hidden){
return;
}
var section = toggle.closest('[data-filter-section]');
toggleFilterExpansion(section.dataset.filterSection);
});

document.addEventListener('change',function(e){
var group = FILTER_GROUPS.find(function(candidate){
return e.target.classList.contains(candidate.inputClass);
});
if(group && !e.target.disabled){
applyFilters({group:group.key,inputClass:group.inputClass,value:e.target.value});
}
});

document.addEventListener('keydown',function(e){
if((e.key === ' ' || e.key === 'Enter') && e.target.classList.contains('filter-option')){
e.preventDefault();
var input = e.target.querySelector('input');
if(!input.disabled){ input.click(); }
}
});

function normalizeSearchText(value){
return String(value || '')
.normalize('NFD')
.replace(/[\u0300-\u036f]/g,'')
.replace(/ß/g,'ss')
.toLowerCase()
.trim()
.replace(/\\s+/g,' ');
}

function getSearchScore(item,query){
var store = item.store;
var name = normalizeSearchText(store.StoreName);
var city = normalizeSearchText(store.City);
var zip = normalizeSearchText(store.PostalCode);
var address = normalizeSearchText(store.Address);
if(name === query || city === query || zip === query || address === query){ return 0; }
if(name.startsWith(query)){ return 1; }
if(city.startsWith(query) || zip.startsWith(query)){ return 2; }
if(name.includes(query)){ return 3; }
if(city.includes(query) || zip.includes(query)){ return 4; }
if(address.includes(query)){ return 5; }
return Infinity;
}

function findSearchResults(query){
return pageScopeMarkers
.map(function(item){ return {item:item,score:getSearchScore(item,query)}; })
.filter(function(result){ return Number.isFinite(result.score); })
.sort(function(a,b){
return a.score - b.score ||
normalizeSearchText(a.item.store.StoreName).localeCompare(normalizeSearchText(b.item.store.StoreName)) ||
String(a.item.store.ID).localeCompare(String(b.item.store.ID));
});
}

function hideSearchResults(){
var results = document.getElementById('searchResults');
results.hidden = true;
document.getElementById('locationSearch').setAttribute('aria-expanded','false');
}

function renderSearchResults(matches){
var results = document.getElementById('searchResults');
results.innerHTML = '';
searchResultItems = matches.slice(0,10).map(function(match){ return match.item; });

if(!matches.length){
var empty = document.createElement('div');
empty.className = 'search-result-status';
empty.textContent = 'No matching locations';
results.appendChild(empty);
}else{
if(matches.length > 10){
var status = document.createElement('div');
status.className = 'search-result-status';
status.textContent = matches.length + ' matches — showing first 10';
results.appendChild(status);
}
searchResultItems.forEach(function(item,index){
var button = document.createElement('button');
var name = document.createElement('span');
var meta = document.createElement('span');
var zipCity = [item.store.PostalCode,item.store.City].filter(Boolean).join(' ');
button.type = 'button';
button.className = 'search-result-button';
button.dataset.resultIndex = index;
button.setAttribute('role','option');
name.className = 'search-result-name';
name.textContent = item.store.StoreName || 'Unnamed location';
meta.className = 'search-result-meta';
meta.textContent = (zipCity || '-') + ' · ' + (item.store.Address || '-');
button.appendChild(name);
button.appendChild(meta);
results.appendChild(button);
});
}

results.hidden = false;
document.getElementById('locationSearch').setAttribute('aria-expanded','true');
}

function addRequiredFilterValue(selector,value){
var checkbox = value && document.querySelector(selector + '[value="' + CSS.escape(value) + '"]');
if(checkbox){
checkbox.checked = true;
return true;
}
document.querySelectorAll(selector).forEach(function(cb){ cb.checked = false; });
return false;
}

function adjustFiltersForSearchTarget(item){
var selections = getFilterSelections();
var state = stateNameMap[item.store.State];
var category = item.store.StoreType;

if(selections.states.length && !selections.states.includes(state)){
addRequiredFilterValue('.stateCheckbox',state);
}
if(selections.categories.length && !selections.categories.includes(category)){
addRequiredFilterValue('.categoryCheckbox',category);
}
if(mapView.mode === 'overview' && selections.brands.length){
var targetBrands = BRAND_CONFIG.filter(function(brand){ return itemMatchesBrand(item,brand); });
var selectedTargetBrand = targetBrands.some(function(brand){ return selections.brands.includes(brand.slug); });
if(!selectedTargetBrand){
if(targetBrands.length){
addRequiredFilterValue('.brandCheckbox',targetBrands[0].slug);
}else{
document.querySelectorAll('.brandCheckbox').forEach(function(cb){ cb.checked = false; });
}
}
}
}

function focusSearchTarget(item){
if(isClusterMode){
markerCluster.zoomToShowLayer(item.marker,function(){
setTimeout(function(){ item.marker.openPopup(); },80);
});
return;
}
var marker = item.displayMarker;
if(!marker){ return; }
map.panTo(marker.getLatLng(),{animate:true});
setTimeout(function(){ marker.openPopup(); },300);
}

function selectSearchResult(item){
adjustFiltersForSearchTarget(item);
var filtered = applyFilters();
hideSearchResults();
document.getElementById('locationSearch').blur();
if(isMobileFiltersLayout()){
setMobileFiltersOpen(false);
}
if(filtered.includes(item)){
focusSearchTarget(item);
}
}

function initializeSearch(){
var input = document.getElementById('locationSearch');
var results = document.getElementById('searchResults');
input.addEventListener('input',function(){
var query = normalizeSearchText(input.value);
if(query.length < 2){
hideSearchResults();
return;
}
renderSearchResults(findSearchResults(query));
});
results.addEventListener('click',function(e){
var button = e.target.closest('.search-result-button');
if(!button){ return; }
var item = searchResultItems[Number(button.dataset.resultIndex)];
if(item){ selectSearchResult(item); }
});
document.addEventListener('click',function(e){
if(!document.getElementById('searchControl').contains(e.target)){
hideSearchResults();
}
});
input.addEventListener('keydown',function(e){
if(e.key === 'Escape'){
hideSearchResults();
input.blur();
}
});
}

function isMobileFiltersLayout(){
return window.matchMedia('(max-width: 768px)').matches;
}

function setMobileFiltersOpen(open){
if(!isMobileFiltersLayout()){
return;
}
mobileFiltersOpen = Boolean(open);
document.getElementById('filter-panel').style.display = mobileFiltersOpen ? 'block' : 'none';
document.getElementById('openFilterBtn').style.display = 'block';
document.getElementById('openFilterBtn').setAttribute('aria-expanded',mobileFiltersOpen ? 'true' : 'false');
}

function initializeMobileFilters(){
var openButton = document.getElementById('openFilterBtn');
var closeButton = document.getElementById('closeFilterBtn');
var wasMobile = isMobileFiltersLayout();
openButton.setAttribute('aria-controls','filter-panel');
openButton.addEventListener('click',function(e){
if(!isMobileFiltersLayout()){ return; }
e.stopPropagation();
setMobileFiltersOpen(!mobileFiltersOpen);
});
closeButton.addEventListener('click',function(){
if(isMobileFiltersLayout()){ setMobileFiltersOpen(false); }
});
map.on('click',function(){
if(isMobileFiltersLayout()){ setMobileFiltersOpen(false); }
});
window.addEventListener('resize',function(){
var mobile = isMobileFiltersLayout();
if(mobile === wasMobile){ return; }
wasMobile = mobile;
if(mobile){
setMobileFiltersOpen(false);
}else{
document.getElementById('filter-panel').style.display = 'block';
openButton.style.display = 'none';
}
updateMobileFilterButton(getFilterSelections());
});
if(wasMobile){
setMobileFiltersOpen(false);
}
}

applyViewTitle();
pageScopeMarkers = getPageScopeMarkers();
window.pageScopeMarkers = pageScopeMarkers;
rebuildFacetCounts(pageScopeMarkers);

var initialSelections = {
states:[],
categories:[],
brands:mapView.mode === 'brand' && mapView.brand ? [mapView.brand.slug] : []
};
renderFilterSections(initialSelections,null);
applyFilters();
initializeSearch();
initializeMobileFilters();
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(html: str, old: str, new: str, label: str) -> str:
    if html.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label} anchor")
    return html.replace(old, new, 1)


def load_brand_config() -> list[dict[str, str]]:
    brands = json.loads(BRAND_CONFIG_SOURCE.read_text(encoding="utf-8"))
    if not isinstance(brands, list) or not brands:
        raise RuntimeError("Brand configuration must contain at least one brand")
    required = {"slug", "label", "column"}
    if any(set(brand) != required or not all(brand.values()) for brand in brands):
        raise RuntimeError("Each brand configuration requires slug, label, and column")
    if len({brand["slug"] for brand in brands}) != len(brands):
        raise RuntimeError("Brand slugs must be unique")
    return brands


def feature_bootstrap(brands: list[dict[str, str]]) -> str:
    config = json.dumps(brands, ensure_ascii=False)
    return f"""var BRAND_CONFIG = {config};

function resolveMapView(){{
var segments = window.location.pathname.split('/').filter(Boolean);
var lastSegment = segments.length ? segments[segments.length - 1] : '';
if(lastSegment === 'network-overview'){{
return {{mode:'overview',brand:null}};
}}
var brand = BRAND_CONFIG.find(function(candidate){{ return candidate.slug === lastSegment; }});
if(brand){{
return {{mode:'brand',brand:brand}};
}}
return {{mode:'neutral',brand:null}};
}}

var mapView = resolveMapView();

"""


def build_page(brands: list[dict[str, str]], *, preview: bool, noindex: bool) -> str:
    html = SOURCE.read_text(encoding="utf-8")
    if preview:
        html = replace_once(
            html,
            "<title>VPL Germany Network Map</title>",
            "<title>VPL Germany Network Map Preview</title>\n" + PREVIEW_META,
            "preview title",
        )
        html = replace_once(html, "<body>", "<body>\n" + PREVIEW_BADGE, "preview body start")
    elif noindex:
        html = replace_once(
            html,
            "<title>VPL Germany Network Map</title>",
            "<title>VPL Germany Network Map</title>\n" + PREVIEW_META,
            "private-page title",
        )
    html = replace_once(html, "</style>", PREVIEW_CSS + "\n</style>", "style end")
    html = replace_once(
        html,
        '<button id="openFilterBtn">',
        SEARCH_MARKUP + '\n<button id="openFilterBtn">',
        "search control",
    )

    filter_start = html.index('<div id="stateFilterContainer">')
    filter_end = html.index('\n\n</div>\n\n\n</div>\n\n<div id="mapStyleBar">', filter_start)
    html = html[:filter_start] + FILTER_MARKUP + html[filter_end:]

    html = replace_once(
        html,
        "<script>\n\nvar map =",
        "<script>\n\n" + feature_bootstrap(brands) + "var map =",
        "map bootstrap",
    )
    if preview:
        html = replace_once(
            html,
            "'VPL门店地图信息.csv?v=' + Date.now(),",
            "'/preview/data/locations.csv?v=' + Date.now(),",
            "preview CSV path",
        )
    else:
        html = replace_once(
            html,
            "'VPL门店地图信息.csv?v=' + Date.now(),",
            "'/VPL门店地图信息.csv?v=' + Date.now(),",
            "production CSV path",
        )
    html = replace_once(
        html,
        "fetch('Germany_border_sehr_hoch.geo.json')",
        "fetch('/Germany_border_sehr_hoch.geo.json')",
        "border GeoJSON path",
    )
    html = replace_once(
        html,
        "fetch('2_hoch.geo_1.4M.json')",
        "fetch('/2_hoch.geo_1.4M.json')",
        "state GeoJSON path",
    )

    filter_logic_start = html.index('function applyFilters(){')
    filter_logic_end = html.index("\nfetch('/Germany_border_sehr_hoch.geo.json')", filter_logic_start)
    html = html[:filter_logic_start] + FILTER_LOGIC + html[filter_logic_end:]
    return "\n".join(line.rstrip() for line in html.splitlines()) + "\n"


def build_preview() -> None:
    brands = load_brand_config()
    if not CANDIDATE_CSV.is_file():
        raise RuntimeError(f"Candidate CSV is missing: {CANDIDATE_CSV}")

    page = build_page(brands, preview=True, noindex=True)
    PREVIEW_DIR.mkdir(exist_ok=True)
    PREVIEW_DATA.parent.mkdir(exist_ok=True)
    shutil.copyfile(CANDIDATE_CSV, PREVIEW_DATA)

    source_hash = sha256(CANDIDATE_CSV)
    preview_hash = sha256(PREVIEW_DATA)
    if source_hash != preview_hash:
        raise RuntimeError("Preview CSV copy hash does not match candidate source")
    PREVIEW_DATA_HASH.write_text(
        f"{source_hash}  VPL门店地图信息.csv\n"
        f"{preview_hash}  preview/data/locations.csv\n",
        encoding="utf-8",
    )

    for relative_target in (
        Path("index.html"),
        Path("network-overview/index.html"),
        Path("geekbar/index.html"),
        Path("dojo/index.html"),
    ):
        target = PREVIEW_DIR / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build_preview()
