import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "map_template.html"
BRAND_CONFIG_SOURCE = ROOT / "scripts" / "brand_config.json"
CANDIDATE_CSV = ROOT / "map data" / "VPL门店地图信息_20260831_1644_English.csv"
PREVIEW_DIR = ROOT / "preview"
PREVIEW_DATA = PREVIEW_DIR / "data" / "locations.csv"
PREVIEW_DATA_HASH = PREVIEW_DIR / "data" / "locations.sha256"

PREVIEW_META = '<meta name="robots" content="noindex,nofollow">'
PREVIEW_BADGE = """<div id="previewEnvBadge">
PREVIEW ENVIRONMENT
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

.filter-section[hidden]{
display:none;
}

@media (max-width: 768px){
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
top:12px;
right:12px;
font-size:11px;
padding:8px 12px;
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
</div>"""

FILTER_LOGIC = """
var FILTER_GROUPS = [
{key:'states',inputClass:'stateCheckbox',rowClass:'state-item',containerId:'stateFilter',sectionId:'stateFilterContainer',summaryId:'stateSelectionSummary',toggleId:'toggleStateFilter'},
{key:'categories',inputClass:'categoryCheckbox',rowClass:'category-item',containerId:'categoryFilter',sectionId:'categoryFilterContainer',summaryId:'categorySelectionSummary',toggleId:'toggleCategoryFilter'},
{key:'brands',inputClass:'brandCheckbox',rowClass:'brand-item',containerId:'brandFilter',sectionId:'brandFilterContainer',summaryId:'brandSelectionSummary',toggleId:'toggleBrandFilter'}
];

var expandedFilterSection = null;

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
var row = document.createElement('div');
row.className = group.rowClass + ' filter-item' + (selected ? ' is-selected' : '');
row.innerHTML =
'<label class="filter-chip filter-option" tabindex="0" role="checkbox" aria-checked="' + selected + '">' +
'<input type="checkbox" class="' + group.inputClass + '" value="' + item.value + '">' +
'<span class="chip-name">' + item.label + '</span>' +
'<span class="chip-count">' + item.count + '</span>' +
'</label>';
row.querySelector('input').checked = selected;
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
}

function applyFilters(focusTarget){
var selections = getFilterSelections();
ensureAutoExpansion(selections,focusTarget && focusTarget.group);

var filteredMarkers = allMarkers.filter(function(item){
var state = stateNameMap[item.store.State];
var category = item.store.StoreType;
var stateMatch = selections.states.length === 0 || selections.states.includes(state);
var categoryMatch = selections.categories.length === 0 || selections.categories.includes(category);
var brandMatch = selections.brands.length === 0 || selections.brands.some(function(slug){
var brand = BRAND_CONFIG.find(function(candidate){ return candidate.slug === slug; });
return brand && item.store[brand.column] === '1';
});
return stateMatch && categoryMatch && brandMatch;
});

window.renderMarkers(filteredMarkers);
updateStats(filteredMarkers);
renderFilterSections(selections,focusTarget);
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
if(group){
applyFilters({group:group.key,inputClass:group.inputClass,value:e.target.value});
}
});

document.addEventListener('keydown',function(e){
if((e.key === ' ' || e.key === 'Enter') && e.target.classList.contains('filter-option')){
e.preventDefault();
e.target.querySelector('input').click();
}
});

applyViewTitle();

var initialSelections = {
states:[],
categories:[],
brands:mapView.mode === 'brand' && mapView.brand ? [mapView.brand.slug] : []
};
renderFilterSections(initialSelections,null);
applyFilters();
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
        f"{source_hash}  map data/VPL门店地图信息_20260831_1644_English.csv\n"
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
