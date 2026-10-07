import hashlib
import json
import shutil
from pathlib import Path

from validate_locations import configured_brands, validate_or_exit


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
<button id="openSearchBtn" type="button" aria-controls="locationSearch" aria-expanded="false">Search</button>
<label class="search-input-wrap" for="locationSearch">
<span class="search-icon" aria-hidden="true">⌕</span>
<input id="locationSearch" type="search" inputmode="search" autocomplete="off" placeholder="Search locations…" aria-label="Search locations" aria-controls="searchResults" aria-expanded="false">
</label>
<button id="closeSearchBtn" type="button" aria-label="Close search">×</button>
<div id="showingCount" aria-live="polite">Showing 0 of 0 locations</div>
<div id="searchResults" role="listbox" aria-label="Location search results" hidden></div>
</div>
"""
AREA_CONTROL_MARKUP = """<div id="areaControl" aria-live="polite" hidden>
<button id="searchAreaBtn" type="button">Search this area</button>
<span id="areaCount" hidden></span>
<button id="showAllMapBtn" type="button" hidden>Show all</button>
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

#openSearchBtn,
#closeSearchBtn{
display:none;
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

#shareFeedback{
margin-top:4px;
padding:5px 7px;
border-radius:6px;
background:rgba(239,246,255,.9);
color:#1E3A8A;
font-size:12px;
line-height:1.4;
overflow-wrap:anywhere;
}

#shareFeedback[hidden]{
display:none;
}

#shareViewBtn{
width:100%;
min-height:32px;
padding:5px 8px;
border:1px solid #94A3B8;
border-radius:6px;
background:rgba(255,255,255,.72);
color:#1E40AF;
font:inherit;
font-size:12px;
font-weight:700;
cursor:pointer;
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

#areaControl{
position:absolute;
top:20px;
left:50%;
transform:translateX(-50%);
z-index:10003;
display:flex;
align-items:center;
gap:8px;
max-width:calc(100vw - 40px);
padding:6px 8px;
border:1px solid rgba(255,255,255,.95);
border-radius:10px;
background:rgba(255,255,255,.9);
box-shadow:0 8px 24px rgba(15,23,42,.15);
white-space:nowrap;
}
#areaControl[hidden],
#areaPanel[hidden]{display:none !important;}
#areaControl button,
#areaPanel button{
border:0;
border-radius:6px;
padding:6px 9px;
background:#EFF6FF;
color:#1D4ED8;
font:inherit;
font-size:12px;
font-weight:700;
cursor:pointer;
}
#areaCount{font-size:12px;font-weight:700;color:#334155;}
#areaPanel{
display:flex;
align-items:center;
justify-content:space-between;
gap:8px;
font-size:12px;
color:#334155;
}
#locationsPanel{display:none;}
#storeDetailPanel{display:none;}

@media (min-width: 769px){
:root{--desktop-panel-width:clamp(320px,26vw,380px);}
#map{width:calc(100% - var(--desktop-panel-width));margin-left:var(--desktop-panel-width);}
#filter-panel{
top:0;
left:0;
width:var(--desktop-panel-width);
height:100vh;
height:100dvh;
max-height:none;
padding:16px;
border-radius:0 12px 12px 0;
background:rgba(248,250,252,.95);
z-index:10000;
}
#filter-panel .panel-content{padding-top:76px;}
#searchControl{top:16px;left:16px;width:calc(var(--desktop-panel-width) - 32px);z-index:10010;}
#mapStyleBar{left:calc(var(--desktop-panel-width) + 20px);}
#mapFloatingTitle,
#mapFloatingTitle.is-brand-title{
left:calc(var(--desktop-panel-width) + (100vw - var(--desktop-panel-width))/2);
width:min(780px,calc(100vw - var(--desktop-panel-width) - 40px));
}
#areaControl{left:calc(var(--desktop-panel-width) + (100vw - var(--desktop-panel-width))/2);}
#locationsPanel{display:block;min-width:0;border-top:1px solid #CBD5E1;padding-top:8px;}
#locationsHeading{margin:0 0 8px;font-size:15px;color:#0F172A;}
#locationsList{max-height:50dvh;min-height:130px;overflow-y:auto;overflow-x:hidden;}
#storeDetailPanel{min-width:0;overflow-y:auto;overflow-x:hidden;padding:4px 0 20px;color:#0F172A;}
#filter-panel.is-detail .results-body,
#filter-panel.is-detail #statsPanel,
body.desktop-detail-open #showingCount,
#filter-panel.is-detail #filterSections,
#filter-panel.is-detail #clearAllFilters,
#filter-panel.is-detail #shareViewBtn,
#filter-panel.is-detail #shareFeedback{display:none !important;}
#filter-panel.is-detail #storeDetailPanel{display:block;}
#detailBackBtn,#detailShowAllBtn,#detailShareBtn{min-height:36px;padding:7px 10px;border:1px solid #94A3B8;border-radius:7px;background:white;color:#1D4ED8;font:inherit;font-weight:700;cursor:pointer;}
#detailBackBtn{margin-bottom:12px;}
#detailShowAllBtn{margin-top:10px;}
#detailShowAllBtn[hidden]{display:none;}
#detailShareBtn{display:block;margin-top:10px;}
#detailContent{overflow-wrap:anywhere;}
#detailContent h3{font-size:19px !important;}
#detailContent img{max-width:100%;}
#detailContent .detail-media{margin:0 0 14px !important;}
#detailShareFeedback{margin-top:8px;color:#1E3A8A;font-size:12px;}
#detailShareFeedback[hidden]{display:none;}
.location-row{display:block;width:100%;box-sizing:border-box;margin:0 0 6px;padding:9px;border:1px solid #CBD5E1;border-radius:8px;background:rgba(255,255,255,.72);text-align:left;cursor:pointer;}
.location-row.is-active{border-color:#2563EB;background:#DBEAFE;}
.location-row-name{display:block;font-size:13px;font-weight:700;color:#0F172A;overflow-wrap:anywhere;}
.location-row-meta{display:block;margin:3px 0;font-size:11px;color:#475569;}
.location-row-directions{font-size:12px;font-weight:700;color:#1D4ED8;}
body.desktop-panel-collapsed #map{width:100%;margin-left:0;}
body.desktop-panel-collapsed #filter-panel,
body.desktop-panel-collapsed #searchControl{display:none !important;}
body.desktop-panel-collapsed #openFilterBtn{display:block;top:20px;left:20px;}
body.desktop-panel-collapsed #mapStyleBar{left:20px;}
body.desktop-panel-collapsed #mapFloatingTitle,
body.desktop-panel-collapsed #mapFloatingTitle.is-brand-title{left:50%;width:min(780px,calc(100vw - 40px));}
body.desktop-panel-collapsed #areaControl{left:50%;}
}

@media (max-width: 768px){
:root{
--mobile-safe-top:env(safe-area-inset-top,0px);
--mobile-safe-bottom:env(safe-area-inset-bottom,0px);
--mobile-top-row:calc(10px + var(--mobile-safe-top));
--mobile-panel-top:calc(var(--mobile-top-row) + 48px);
--mobile-style-bottom:calc(6px + var(--mobile-safe-bottom));
--mobile-panel-bottom:calc(var(--mobile-style-bottom) + 52px + 12px);
--map-z-style:1150;
--map-z-counter:1200;
--map-z-panel:1300;
--map-z-controls:1400;
--map-z-popup:1500;
--map-z-modal:2000;
}

#map{
height:100vh;
height:100dvh;
}

#searchControl{
top:var(--mobile-top-row);
z-index:var(--map-z-controls);
left:10px;
width:calc(100vw - 132px);
min-width:0;
height:38px;
display:flex;
align-items:center;
gap:5px;
}

#openSearchBtn,
#closeSearchBtn{
display:block;
flex:none;
height:38px;
padding:0 10px;
border:1px solid rgba(255,255,255,.95);
border-radius:10px;
background:rgba(255,255,255,.86);
color:#0F172A;
font:inherit;
font-size:13px;
font-weight:700;
box-shadow:0 8px 24px rgba(15,23,42,.10);
cursor:pointer;
}

#searchControl .search-input-wrap,
#searchControl #closeSearchBtn{
display:none;
}

#searchControl .search-input-wrap{
flex:1;
min-width:0;
}

#locationSearch{
width:100%;
min-width:0;
font-size:16px;
}

#searchControl.is-search-open{
left:10px;
right:10px;
width:auto;
max-width:none;
}

#searchControl.is-search-open + #openFilterBtn{
visibility:hidden;
}

#searchControl.is-search-open #openSearchBtn,
#searchControl.is-search-open #showingCount{
display:none;
}

#searchControl.is-search-open .search-input-wrap{
display:flex;
flex:1;
min-width:0;
}

#searchControl.is-search-open #closeSearchBtn{
display:block;
flex:none;
}

#showingCount{
min-width:0;
margin:0;
padding:2px 5px;
white-space:nowrap;
font-size:10px;
}

#searchResults{
top:42px;
max-height:32vh;
max-height:32dvh;
z-index:1;
}

#locationCounter{
top:var(--mobile-panel-top);
right:10px;
z-index:var(--map-z-counter);
}

body.mobile-filters-open #locationCounter,
body.mobile-search-open #locationCounter{
visibility:hidden;
}

#filter-panel{
display:none;
top:var(--mobile-panel-top);
left:10px;
width:min(280px,calc(100vw - 20px));
max-height:calc(100vh - var(--mobile-panel-top) - var(--mobile-panel-bottom));
max-height:calc(100dvh - var(--mobile-panel-top) - var(--mobile-panel-bottom));
overflow-y:auto;
overscroll-behavior:contain;
z-index:var(--map-z-panel);
}

#mapStyleBar{
bottom:var(--mobile-style-bottom);
z-index:var(--map-z-style);
}
#areaPanel,
#locationsPanel{display:none !important;}
#areaControl{
top:calc(var(--mobile-panel-top) + 110px);
max-width:calc(100vw - 40px);
z-index:var(--map-z-panel);
}
body.mobile-search-open #areaControl,
body.mobile-filters-open #areaControl,
body:has(.leaflet-popup-pane .leaflet-popup) #areaControl{display:none !important;}
#previewEnvBadge{top:calc(var(--mobile-panel-top) + 84px);}

#openFilterBtn{
display:block;
top:var(--mobile-top-row);
left:auto;
right:10px;
height:38px;
padding:0 10px;
z-index:var(--map-z-controls);
}

.leaflet-popup-pane{
z-index:var(--map-z-popup) !important;
}

#photoModal{
z-index:var(--map-z-modal);
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
top:calc(var(--mobile-panel-top) + 84px);
right:10px;
z-index:1100;
font-size:10px;
padding:7px 10px;
}

body:has(.leaflet-popup-pane .leaflet-popup) #previewEnvBadge{
visibility:hidden;
}
}

@media (max-width: 768px) and (max-height: 500px){
/* In short landscape, the photo card uses the same clear zone as the filter panel. */
.leaflet-popup-content-wrapper{
box-sizing:border-box;
max-height:calc(100vh - var(--mobile-panel-top) - var(--mobile-panel-bottom));
max-height:calc(100dvh - var(--mobile-panel-top) - var(--mobile-panel-bottom));
overflow-y:auto;
}
#popupImage{
height:100px !important;
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
<button id="shareViewBtn" type="button">Share view</button>
<div id="shareFeedback" role="status" aria-live="polite" hidden></div>
</div>
<div class="results-body">
<section id="areaPanel" aria-label="Area results" hidden>
<span id="areaStatus"></span>
<button id="showAllPanelBtn" type="button">Show all</button>
</section>
<section id="locationsPanel" aria-labelledby="locationsHeading">
<h2 id="locationsHeading">Locations</h2>
<div id="locationsList" role="list"></div>
</section>
</div>
<section id="storeDetailPanel" aria-label="Store details" hidden>
<button id="detailBackBtn" type="button">← Back to locations</button>
<div id="detailContent"></div>
<button id="detailShowAllBtn" type="button" hidden>Show all</button>
<button id="detailShareBtn" type="button">Share</button>
<div id="detailShareFeedback" role="status" aria-live="polite" hidden></div>
</section>"""

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
var selectedStoreId = null;
var selectedStoreOverlay = null;
var resultsScrollTop = 0;
var suppressPopupSelection = false;
var urlStateReady = false;
var activeArea = null;
var areaPrompt = false;
var userZoomIntent = false;

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
updateShowingCount(filteredMarkers.length,scopeTotal);
}

function updateShowingCount(shown,total){
var count = document.getElementById('showingCount');
count.textContent = isMobileFiltersLayout() ? 'Showing ' + shown + '/' + total :
'Showing ' + shown + ' of ' + total + ' locations';
count.setAttribute('aria-label','Showing ' + shown + ' of ' + total + ' locations');
count.dataset.shown = shown;
count.dataset.total = total;
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

function findScopedStore(id){
return pageScopeMarkers.find(function(item){ return String(item.store.ID).trim() === id; });
}

function updateSelectedStoreView(){
var desktop = !isMobileFiltersLayout();
var item = selectedStoreId && findScopedStore(selectedStoreId);
var panel = document.getElementById('filter-panel');
var detail = document.getElementById('storeDetailPanel');
var content = document.getElementById('detailContent');
var showing = Boolean(desktop && item);
document.getElementById('detailShowAllBtn').hidden = !activeArea;
panel.classList.toggle('is-detail',showing);
document.body.classList.toggle('desktop-detail-open',showing);
detail.hidden = !showing;
if(selectedStoreOverlay){ map.removeLayer(selectedStoreOverlay); selectedStoreOverlay = null; }
if(!showing){ content.replaceChildren(); return; }
if(content.dataset.storeId !== selectedStoreId || !content.firstElementChild){
// The popup is the single source for field, directions and photo markup.
content.innerHTML = buildPopupHtml(item.store);
content.dataset.storeId = selectedStoreId;
var photoData = content.querySelector('.photo-data');
if(photoData){
var media = photoData.parentElement;
media.classList.add('detail-media');
var image = media.querySelector('img');
image.alt = 'Store photo';
// No broken or empty media area while the first photo is being checked.
media.style.display = 'none';
image.addEventListener('load',function(){ media.style.display = 'block'; });
image.addEventListener('error',function(){ media.style.display = 'none'; });
if(image.complete && image.naturalWidth){ media.style.display = 'block'; }
content.firstElementChild.prepend(media);
}
}
selectedStoreOverlay = L.marker(item.marker.getLatLng(),{
icon:L.divIcon({className:'selected-store-pin',html:'<span aria-hidden="true" style="display:block;width:26px;height:26px;border:4px solid #F97316;border-radius:50%;background:#2563EB;box-shadow:0 0 0 3px white,0 3px 12px #334155"></span>',iconSize:[34,34],iconAnchor:[17,17]}),
interactive:false,zIndexOffset:1000
}).addTo(map);
}

function setSelectedStore(id){
var nextId = id && findScopedStore(String(id)) ? String(id) : null;
if(!selectedStoreId && nextId){
resultsScrollTop = document.getElementById('locationsList').scrollTop;
}
selectedStoreId = nextId;
updateSelectedStoreView();
highlightResultRow(nextId);
if(!nextId){ document.getElementById('locationsList').scrollTop = resultsScrollTop; }
syncUrlState();
}

function selectStore(item){
if(!item || !pageScopeMarkers.includes(item)){ return; }
setSelectedStore(String(item.store.ID).trim());
focusSearchTarget(item);
}

function updateResultsList(items){
var list = document.getElementById('locationsList');
var previousScroll = list.scrollTop;
list.replaceChildren();
if(isMobileFiltersLayout()){ return; }
var sorted = items.slice().sort(function(a,b){
return normalizeSearchText(a.store.StoreName).localeCompare(normalizeSearchText(b.store.StoreName)) ||
Number(a.store.ID) - Number(b.store.ID);
});
if(!sorted.length){
var empty = document.createElement('p');
empty.textContent = 'No locations in the current results';
list.appendChild(empty);
return;
}
sorted.forEach(function(item){
var row = document.createElement('div');
var name = document.createElement('span');
var meta = document.createElement('span');
var directions = document.createElement('a');
row.className = 'location-row';
row.dataset.storeId = String(item.store.ID).trim();
row.setAttribute('role','button');
row.tabIndex = 0;
row.setAttribute('aria-label','View ' + (item.store.StoreName || 'location'));
name.className = 'location-row-name';
name.textContent = item.store.StoreName || 'Unnamed location';
meta.className = 'location-row-meta';
meta.textContent = [item.store.City,item.store.StoreType].filter(Boolean).join(' · ');
directions.className = 'location-row-directions';
directions.textContent = 'Directions';
directions.href = 'https://www.google.com/maps/dir/?api=1&destination=' +
String(item.store.Latitude).trim() + ',' + String(item.store.Longitude).trim();
directions.target = '_blank';
directions.rel = 'noopener noreferrer';
row.append(name,meta,directions);
row.classList.toggle('is-active',row.dataset.storeId === selectedStoreId);
list.appendChild(row);
});
list.scrollTop = previousScroll;
}

function highlightResultRow(storeId){
document.querySelectorAll('#locationsList .location-row').forEach(function(row){
var selected = Boolean(storeId && row.dataset.storeId === storeId);
row.classList.toggle('is-active',selected);
if(selected && !document.getElementById('filter-panel').classList.contains('is-detail')){
row.scrollIntoView({block:'nearest'});
}
});
}

function updateAreaControls(){
var control = document.getElementById('areaControl');
control.hidden = !areaPrompt && (!activeArea || !isMobileFiltersLayout());
document.getElementById('searchAreaBtn').hidden = !areaPrompt;
document.getElementById('areaCount').hidden = !activeArea || areaPrompt;
document.getElementById('areaCount').textContent = currentFilteredMarkers.length + ' in this area ·';
document.getElementById('showAllMapBtn').hidden = !activeArea;
var panel = document.getElementById('areaPanel');
panel.hidden = !activeArea;
document.getElementById('areaStatus').textContent = activeArea ?
currentFilteredMarkers.length + ' in this area' : '';
}

function captureAreaBounds(){
var bounds = map.getBounds();
var area = {
west:Math.max(-180,bounds.getWest()),
south:Math.max(-90,bounds.getSouth()),
east:Math.min(180,bounds.getEast()),
north:Math.min(90,bounds.getNorth())
};
return area.west < area.east && area.south < area.north ? area : null;
}

function parseAreaBounds(value){
if(!value){ return null; }
var parts = value.split(',');
if(parts.length !== 4 || parts.some(function(part){
return !/^[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)$/.test(part);
})){ return null; }
var numbers = parts.map(Number);
var west = numbers[0], south = numbers[1], east = numbers[2], north = numbers[3];
if(!numbers.every(Number.isFinite) || west < -180 || east > 180 ||
south < -90 || north > 90 || west >= east || south >= north){ return null; }
return {west:west,south:south,east:east,north:north};
}

function initializeAreaControls(){
function showAreaPrompt(){
if(!urlStateReady){ return; }
areaPrompt = true;
updateAreaControls();
}
map.on('dragend',showAreaPrompt);
markerCluster.on('clusterclick',showAreaPrompt);
var container = map.getContainer();
function noteZoomIntent(){
userZoomIntent = true;
setTimeout(function(){ userZoomIntent = false; },1200);
}
container.addEventListener('wheel',noteZoomIntent,{passive:true});
container.addEventListener('dblclick',noteZoomIntent,true);
container.addEventListener('keydown',function(event){
if(['+','=','-','_','Add','Subtract'].includes(event.key)){
noteZoomIntent();
}
},true);
container.addEventListener('touchstart',function(event){
if(event.touches.length > 1){ noteZoomIntent(); }
},{passive:true});
container.addEventListener('click',function(event){
if(event.target.closest('.leaflet-control-zoom-in,.leaflet-control-zoom-out')){
noteZoomIntent();
}
},true);
map.on('zoomend',function(){
if(userZoomIntent){ userZoomIntent = false; showAreaPrompt(); }
});
document.getElementById('searchAreaBtn').addEventListener('click',function(){
if(selectedStoreId){ setSelectedStore(null); }
activeArea = captureAreaBounds();
areaPrompt = false;
applyFilters();
});
function showAll(){
activeArea = null;
areaPrompt = false;
applyFilters();
}
document.getElementById('showAllMapBtn').addEventListener('click',showAll);
document.getElementById('showAllPanelBtn').addEventListener('click',showAll);
document.getElementById('detailShowAllBtn').addEventListener('click',showAll);
}

function applyFilters(focusTarget){
var selections = getFilterSelections();
ensureAutoExpansion(selections,focusTarget && focusTarget.group);

var userFiltered = pageScopeMarkers.filter(function(item){
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
var filteredMarkers = activeArea ? userFiltered.filter(function(item){
var point = item.marker.getLatLng();
return point.lng >= activeArea.west && point.lng <= activeArea.east &&
point.lat >= activeArea.south && point.lat <= activeArea.north;
}) : userFiltered;

window.renderMarkers(filteredMarkers);
updateStats(filteredMarkers);
renderFilterSections(selections,focusTarget);
updateMobileFilterButton(selections);
updateResultsList(filteredMarkers);
updateAreaControls();
updateSelectedStoreView();
if(urlStateReady){ syncUrlState(); }
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

function replaceFilterDimension(selector,value){
var checkbox = value && document.querySelector(selector + '[value="' + CSS.escape(value) + '"]');
document.querySelectorAll(selector).forEach(function(cb){ cb.checked = cb === checkbox; });
}

function adjustFiltersForSearchTarget(item){
var selections = getFilterSelections();
var state = stateNameMap[item.store.State];
var category = item.store.StoreType;

if(selections.states.length && (selections.states.length !== 1 || selections.states[0] !== state)){
replaceFilterDimension('.stateCheckbox',state);
}
if(selections.categories.length && (selections.categories.length !== 1 || selections.categories[0] !== category)){
replaceFilterDimension('.categoryCheckbox',category);
}
if(mapView.mode === 'overview' && selections.brands.length){
var targetBrands = BRAND_CONFIG.filter(function(brand){ return itemMatchesBrand(item,brand); });
var selectedTargetBrand = targetBrands.some(function(brand){ return selections.brands.includes(brand.slug); });
if(!selectedTargetBrand || selections.brands.some(function(slug){
return !targetBrands.some(function(brand){ return brand.slug === slug; });
})){
var compatibleBrand = selections.brands.find(function(slug){
return targetBrands.some(function(brand){ return brand.slug === slug; });
});
replaceFilterDimension('.brandCheckbox',compatibleBrand || (targetBrands.length ? targetBrands[0].slug : null));
}
}
}

function focusSearchTarget(item){
if(!isMobileFiltersLayout()){
map.panTo(item.marker.getLatLng(),{animate:true});
return;
}
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
activeArea = null;
areaPrompt = false;
adjustFiltersForSearchTarget(item);
var filtered = applyFilters();
hideSearchResults();
document.getElementById('locationSearch').blur();
if(isMobileFiltersLayout()){
setMobileFiltersOpen(false);
setMobileSearchOpen(false);
}
if(filtered.includes(item)){
selectStore(item);
}
}

var viewportSyncTimer = null;
function syncMapSizeAfterViewportChange(){
clearTimeout(viewportSyncTimer);
viewportSyncTimer = setTimeout(function(){
requestAnimationFrame(function(){ map.invalidateSize({pan:false}); });
},80);
}

function setMobileSearchOpen(open){
if(!isMobileFiltersLayout()){
return;
}
var control = document.getElementById('searchControl');
var input = document.getElementById('locationSearch');
control.classList.toggle('is-search-open',Boolean(open));
document.body.classList.toggle('mobile-search-open',Boolean(open));
document.getElementById('openSearchBtn').setAttribute('aria-expanded',open ? 'true' : 'false');
if(open){
setMobileFiltersOpen(false);
input.focus();
}else{
hideSearchResults();
input.value = '';
input.blur();
}
requestAnimationFrame(syncMapSizeAfterViewportChange);
}

function initializeSearch(){
var input = document.getElementById('locationSearch');
var results = document.getElementById('searchResults');
document.getElementById('openSearchBtn').addEventListener('click',function(){
setMobileSearchOpen(true);
});
document.getElementById('closeSearchBtn').addEventListener('click',function(){
setMobileSearchOpen(false);
});
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
if(isMobileFiltersLayout()){
setMobileSearchOpen(false);
}else{
hideSearchResults();
}
}
});
input.addEventListener('keydown',function(e){
if(e.key === 'Escape'){
if(isMobileFiltersLayout()){
setMobileSearchOpen(false);
}else{
hideSearchResults();
input.blur();
}
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
document.body.classList.toggle('mobile-filters-open',mobileFiltersOpen);
document.getElementById('filter-panel').style.display = mobileFiltersOpen ? 'block' : 'none';
document.getElementById('openFilterBtn').style.display = 'block';
document.getElementById('openFilterBtn').setAttribute('aria-expanded',mobileFiltersOpen ? 'true' : 'false');
}

function setDesktopPanelCollapsed(collapsed){
if(isMobileFiltersLayout()){ return; }
document.body.classList.toggle('desktop-panel-collapsed',Boolean(collapsed));
document.getElementById('filter-panel').style.display = collapsed ? 'none' : 'block';
document.getElementById('openFilterBtn').style.display = collapsed ? 'block' : 'none';
requestAnimationFrame(function(){ map.invalidateSize({pan:false}); });
}

function initializeDesktopPanel(){
var list = document.getElementById('locationsList');
function viewRow(row){
var storeId = row.dataset.storeId;
var item = pageScopeMarkers.find(function(candidate){
return String(candidate.store.ID).trim() === storeId;
});
if(item && currentFilteredMarkers.includes(item)){ selectStore(item); }
}
list.addEventListener('click',function(event){
if(event.target.closest('.location-row-directions')){ return; }
var row = event.target.closest('.location-row');
if(row){ viewRow(row); }
});
list.addEventListener('keydown',function(event){
if(event.target.closest('.location-row-directions')){ return; }
var row = event.target.closest('.location-row');
if(row && (event.key === 'Enter' || event.key === ' ')){
event.preventDefault();
viewRow(row);
}
});
}

function initializeMobileFilters(){
var openButton = document.getElementById('openFilterBtn');
var closeButton = document.getElementById('closeFilterBtn');
var wasMobile = isMobileFiltersLayout();
openButton.setAttribute('aria-controls','filter-panel');
openButton.addEventListener('click',function(e){
e.stopPropagation();
if(isMobileFiltersLayout()){
setMobileFiltersOpen(!mobileFiltersOpen);
}else{
setDesktopPanelCollapsed(false);
}
});
closeButton.addEventListener('click',function(){
if(isMobileFiltersLayout()){
setMobileFiltersOpen(false);
}else{
setDesktopPanelCollapsed(true);
}
});
map.on('click',function(){
if(isMobileFiltersLayout()){ setMobileFiltersOpen(false); }
});
window.addEventListener('resize',function(){
syncMapSizeAfterViewportChange();
var mobile = isMobileFiltersLayout();
if(mobile === wasMobile){ return; }
wasMobile = mobile;
if(mobile){
document.body.classList.remove('desktop-panel-collapsed');
setMobileFiltersOpen(false);
setMobileSearchOpen(false);
}else{
document.getElementById('searchControl').classList.remove('is-search-open');
document.body.classList.remove('mobile-search-open','mobile-filters-open');
hideSearchResults();
document.getElementById('filter-panel').style.display = 'block';
openButton.style.display = 'none';
}
if(!mobile){
suppressPopupSelection = true;
map.closePopup();
suppressPopupSelection = false;
}
updateSelectedStoreView();
if(selectedStoreId && mobile){
var selected = findScopedStore(selectedStoreId);
if(selected){ focusSearchTarget(selected); }
}
updateResultsList(currentFilteredMarkers);
updateAreaControls();
var count = document.getElementById('showingCount');
updateShowingCount(Number(count.dataset.shown),Number(count.dataset.total));
updateMobileFilterButton(getFilterSelections());
});
if(window.visualViewport){
window.visualViewport.addEventListener('resize',syncMapSizeAfterViewportChange);
}
if(wasMobile){
setMobileFiltersOpen(false);
}
}

function shareUrl(){
var url = new URL(window.location.href);
var params = new URLSearchParams();
var selections = getFilterSelections();
selections.states.slice().sort().forEach(function(value){ params.append('state',value); });
selections.categories.slice().sort().forEach(function(value){ params.append('type',value); });
if(mapView.mode === 'overview'){
selections.brands.slice().sort().forEach(function(value){ params.append('brand',value); });
}
if(activeArea){
params.set('bbox',[activeArea.west,activeArea.south,activeArea.east,activeArea.north].map(function(value){
return value.toFixed(6);
}).join(','));
}
if(selectedStoreId){ params.set('id',selectedStoreId); }
var center = map.getCenter();
params.set('lat',center.lat.toFixed(6));
params.set('lng',center.lng.toFixed(6));
params.set('z',String(map.getZoom()));
url.search = params.toString();
return url;
}

function syncUrlState(){
if(!urlStateReady){ return; }
var url = shareUrl();
history.replaceState(history.state,'',url.pathname + url.search + url.hash);
}

function restoreMapView(params){
var values = ['lat','lng','z'].map(function(key){ return params.get(key); });
if(values.some(function(value){ return value === null || !/^[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)$/.test(value); })){
return;
}
var lat = Number(values[0]);
var lng = Number(values[1]);
var zoom = Number(values[2]);
if(!Number.isFinite(lat) || !Number.isFinite(lng) || !Number.isFinite(zoom) ||
Math.abs(lat) > 90 || Math.abs(lng) > 180 || zoom < 0 || zoom > 19){
return;
}
map.setView([lat,lng],zoom,{animate:false});
}

function showShareFeedback(text,detailMode){
var button = document.getElementById(detailMode ? 'detailShareBtn' : 'shareViewBtn');
var feedback = document.getElementById(detailMode ? 'detailShareFeedback' : 'shareFeedback');
clearTimeout(button.feedbackTimer);
if(isMobileFiltersLayout() && !detailMode){
feedback.hidden = true;
button.textContent = text;
}else{
button.textContent = detailMode ? 'Share' : 'Share view';
feedback.textContent = text;
feedback.hidden = false;
}
button.feedbackTimer = setTimeout(function(){
button.textContent = detailMode ? 'Share' : 'Share view';
feedback.hidden = true;
feedback.textContent = '';
},3000);
}

async function copyShareUrl(url,detailMode){
try{
if(navigator.clipboard && navigator.clipboard.writeText){
await navigator.clipboard.writeText(url);
}else{
var field = document.createElement('textarea');
field.value = url;
field.style.position = 'fixed';
field.style.opacity = '0';
document.body.appendChild(field);
field.select();
try{
if(!document.execCommand('copy')){ throw new Error('Copy unavailable'); }
}finally{
field.remove();
}
}
showShareFeedback(isMobileFiltersLayout() ? 'Link copied' :
'Share link copied to clipboard. You can send it to anyone.',detailMode);
}catch(error){
showShareFeedback(isMobileFiltersLayout() ? 'Unable to copy link' :
'Could not copy link. Please try again.',detailMode);
}
}

function initializeUrlState(){
var params = new URLSearchParams(window.location.search);
var selectedStates = new Set(params.getAll('state').filter(function(value){
return Object.prototype.hasOwnProperty.call(stateCount,value);
}));
var selectedTypes = new Set(params.getAll('type').filter(function(value){
return Object.prototype.hasOwnProperty.call(categoryCount,value);
}));
var selectedBrands = new Set(mapView.mode === 'overview' ? params.getAll('brand').filter(function(value){
return BRAND_CONFIG.some(function(brand){ return brand.slug === value; });
}) : []);
document.querySelectorAll('.stateCheckbox').forEach(function(cb){ cb.checked = selectedStates.has(cb.value); });
document.querySelectorAll('.categoryCheckbox').forEach(function(cb){ cb.checked = selectedTypes.has(cb.value); });
if(mapView.mode === 'overview'){
document.querySelectorAll('.brandCheckbox').forEach(function(cb){ cb.checked = selectedBrands.has(cb.value); });
}
activeArea = parseAreaBounds(params.get('bbox'));
applyFilters();
var requestedId = params.get('id');
var target = requestedId && pageScopeMarkers.find(function(item){
return String(item.store.ID).trim() === requestedId;
});
if(target){
activeArea = null;
areaPrompt = false;
adjustFiltersForSearchTarget(target);
if(!applyFilters().includes(target)){ target = null; }
}
urlStateReady = true;
map.on('popupopen',function(e){
var storeId = e.popup._source && e.popup._source.locationStoreId;
var item = storeId && findScopedStore(storeId);
if(!item){ return; }
if(!isMobileFiltersLayout()){
suppressPopupSelection = true;
map.closePopup();
suppressPopupSelection = false;
selectStore(item);
return;
}
setSelectedStore(storeId);
});
map.on('popupclose',function(e){
var storeId = e.popup._source && e.popup._source.locationStoreId;
if(!suppressPopupSelection && isMobileFiltersLayout() && storeId && selectedStoreId === storeId){
setSelectedStore(null);
}
});
map.on('moveend zoomend',syncUrlState);
if(target){
var targetId = String(target.store.ID).trim();
// Let the initial mobile zoom finish before revealing a direct-link marker.
function revealDirectTarget(){
if(selectedStoreId !== targetId){ return; }
if(map._animatingZoom){
map.once('zoomend',revealDirectTarget);
return;
}
map.setView(target.marker.getLatLng(),16,{animate:false});
focusSearchTarget(target);
}
setSelectedStore(targetId);
if(isMobileFiltersLayout()){
setTimeout(revealDirectTarget,600);
}else{
map.setView(target.marker.getLatLng(),16,{animate:false});
}
}else{
restoreMapView(params);
}
syncUrlState();
document.getElementById('detailBackBtn').addEventListener('click',function(){ setSelectedStore(null); });
document.getElementById('detailShareBtn').addEventListener('click',function(){
copyShareUrl(shareUrl().href,true);
});
document.getElementById('shareViewBtn').addEventListener('click',async function(){
var url = shareUrl().href;
if(!isMobileFiltersLayout()){
await copyShareUrl(url);
return;
}
if(navigator.share){
try{
await navigator.share({url:url});
showShareFeedback('Shared');
return;
}catch(error){
if(error && error.name === 'AbortError'){ return; }
}
}
await copyShareUrl(url);
});
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
initializeDesktopPanel();
initializeUrlState();
initializeAreaControls();
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
    return configured_brands(BRAND_CONFIG_SOURCE)


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
    html = replace_once(html, '<div id="mapStyleBar">', AREA_CONTROL_MARKUP + '\n<div id="mapStyleBar">', "area control")

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
    report = validate_or_exit(CANDIDATE_CSV, config=BRAND_CONFIG_SOURCE, template=SOURCE)
    brands = report["brands"]
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

    targets = (Path("index.html"), Path("network-overview/index.html"))
    targets += tuple(Path(brand["slug"]) / "index.html" for brand in brands)
    for relative_target in targets:
        target = PREVIEW_DIR / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build_preview()
