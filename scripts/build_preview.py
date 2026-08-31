import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "index.html"
BRAND_CONFIG_SOURCE = ROOT / "scripts" / "brand_config.json"
CANDIDATE_CSV = ROOT / "map data" / "VPL门店地图信息_20260831_English.csv"
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

.filter-tabs{
display:grid;
grid-template-columns:repeat(3,minmax(0,1fr));
gap:4px;
width:100%;
box-sizing:border-box;
}

.filter-tabs.is-two-tabs{
grid-template-columns:repeat(2,minmax(0,1fr));
}

.filter-tab{
display:flex;
align-items:center;
justify-content:center;
gap:4px;
min-width:0;
height:30px;
padding:0 4px;
border:1px solid rgba(255,255,255,.45);
border-radius:6px;
background:rgba(255,255,255,.18);
color:#334155;
font:inherit;
font-size:12px;
font-weight:700;
cursor:pointer;
}

.filter-tab[aria-selected="true"]{
background:#2563EB;
border-color:#2563EB;
color:#ffffff;
}

.tab-selection-count{
display:flex;
align-items:center;
justify-content:center;
width:16px;
height:16px;
flex:0 0 16px;
border-radius:50%;
background:#E2E8F0;
color:#334155;
font-size:10px;
line-height:1;
}

.filter-tab[aria-selected="true"] .tab-selection-count{
background:#ffffff;
color:#2563EB;
}

.filter-section{
display:none;
}

.filter-section.is-active{
display:block;
}

#stateFilter,
#categoryFilter,
#brandFilter{
width:100%;
max-width:100%;
max-height:260px;
box-sizing:border-box;
overflow-y:auto;
overflow-x:hidden;
}

#brandFilterContainer[hidden],
.filter-tab[hidden]{
display:none;
}

@media (max-width: 768px){
#stateFilter,
#categoryFilter,
#brandFilter{
width:100%;
max-height:28vh;
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
<div id="filterTabs" class="filter-tabs" role="tablist" aria-label="Map filters">
<button type="button" class="filter-tab" role="tab" id="stateFilterTab" aria-selected="true" aria-controls="stateFilterContainer" data-filter-tab="states">States <span class="tab-selection-count">0</span></button>
<button type="button" class="filter-tab" role="tab" id="categoryFilterTab" aria-selected="false" aria-controls="categoryFilterContainer" data-filter-tab="categories">Categories <span class="tab-selection-count">0</span></button>
<button type="button" class="filter-tab" role="tab" id="brandFilterTab" aria-selected="false" aria-controls="brandFilterContainer" data-filter-tab="brand">Brand <span class="tab-selection-count">0</span></button>
</div>

<div id="stateFilterContainer" class="filter-section" role="tabpanel" aria-labelledby="stateFilterTab">
<div style="display:flex;justify-content:space-between;align-items:center;margin:6px 0;">
<div class="filter-title">States</div>
<button id="clearStateFilter" type="button">Clear</button>
</div>
<div id="stateFilter"></div>
</div>

<div id="categoryFilterContainer" class="filter-section" role="tabpanel" aria-labelledby="categoryFilterTab">
<div style="display:flex;justify-content:space-between;align-items:center;margin:6px 0;">
<div class="filter-title">Categories</div>
<button id="clearCategoryFilter" type="button">Clear</button>
</div>
<div id="categoryFilter"></div>
</div>

<div id="brandFilterContainer" class="filter-section" role="tabpanel" aria-labelledby="brandFilterTab">
<div style="display:flex;justify-content:space-between;align-items:center;margin:6px 0;">
<div class="filter-title">Brand</div>
<button id="clearBrandFilter" type="button">All</button>
</div>
<div id="brandFilter"></div>
</div>"""

FILTER_LOGIC = """
function getSelectedValues(selector){
return Array.prototype.map.call(
document.querySelectorAll(selector + ':checked'),
function(cb){ return cb.value; }
);
}

function getSelectedBrands(){
return getSelectedValues('.brandCheckbox');
}

function setFilterTabBadge(tabName,count){
var tab = document.querySelector('[data-filter-tab="' + tabName + '"]');
if(tab){
tab.querySelector('.tab-selection-count').textContent = count;
}
}

function updateFilterTabBadges(){
setFilterTabBadge('states',getSelectedValues('.stateCheckbox').length);
setFilterTabBadge('categories',getSelectedValues('.categoryCheckbox').length);
setFilterTabBadge('brand',getSelectedBrands().length);
}

function setActiveFilterTab(tabName,moveFocus){
var tabs = Array.prototype.filter.call(
document.querySelectorAll('[data-filter-tab]'),
function(tab){ return !tab.hidden; }
);

tabs.forEach(function(tab){
var isActive = tab.dataset.filterTab === tabName;
tab.setAttribute('aria-selected',isActive ? 'true' : 'false');
var section = document.getElementById(tab.getAttribute('aria-controls'));
if(section){
section.classList.toggle('is-active',isActive);
}
if(isActive && moveFocus){
tab.focus();
}
});
}

function renderFilterTabs(){
var isNeutral = mapView.mode === 'neutral';
var tabs = document.getElementById('filterTabs');
var brandTab = document.getElementById('brandFilterTab');
var brandContainer = document.getElementById('brandFilterContainer');

brandTab.hidden = isNeutral;
brandContainer.hidden = isNeutral;
tabs.classList.toggle('is-two-tabs',isNeutral);
setActiveFilterTab(isNeutral ? 'states' : 'brand',false);
}

function renderStateFilter(){
var container = document.getElementById('stateFilter');
container.innerHTML = '';
Object.keys(stateCount).sort().forEach(function(state){
var row = document.createElement('div');
row.className = 'state-item';
row.innerHTML =
'<label class="filter-chip">' +
'<input type="checkbox" class="stateCheckbox" value="' + state + '">' +
'<span class="chip-name">' + state + '</span>' +
'<span class="chip-count">' + stateCount[state] + '</span>' +
'</label>';
container.appendChild(row);
});
}

function renderCategoryFilter(){
var container = document.getElementById('categoryFilter');
container.innerHTML = '';
Object.keys(categoryCount).sort().forEach(function(category){
var row = document.createElement('div');
row.className = 'category-item';
row.innerHTML =
'<label class="filter-chip">' +
'<input type="checkbox" class="categoryCheckbox" value="' + category + '">' +
'<span class="chip-name">' + category + '</span>' +
'<span class="chip-count">' + categoryCount[category] + '</span>' +
'</label>';
container.appendChild(row);
});
}

function renderBrandFilter(){
var container = document.getElementById('brandFilter');
container.innerHTML = '';
if(mapView.mode === 'neutral'){
return;
}
var visibleBrands = mapView.mode === 'brand' ? [mapView.brand] : BRAND_CONFIG;

visibleBrands.forEach(function(brand){
if(!brand){
return;
}
var count = allMarkers.filter(function(item){
return item.store[brand.column] === '1';
}).length;
var row = document.createElement('div');
row.className = 'brand-item';
row.innerHTML =
'<label class="filter-chip">' +
'<input type="checkbox" class="brandCheckbox" value="' + brand.slug + '">' +
'<span class="chip-name">' + brand.label + '</span>' +
'<span class="chip-count">' + count + '</span>' +
'</label>';
container.appendChild(row);
});

if(mapView.mode === 'brand' && mapView.brand){
var defaultBrand = container.querySelector('.brandCheckbox');
if(defaultBrand){
defaultBrand.checked = true;
}
}
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

function applyFilters(){
var selectedStates = getSelectedValues('.stateCheckbox');
var selectedCategories = getSelectedValues('.categoryCheckbox');
var selectedBrands = getSelectedBrands();

var filteredMarkers = allMarkers.filter(function(item){
var state = stateNameMap[item.store.State];
var category = item.store.StoreType;
var stateMatch = selectedStates.length === 0 || selectedStates.includes(state);
var categoryMatch = selectedCategories.length === 0 || selectedCategories.includes(category);
var brandMatch = selectedBrands.length === 0 || selectedBrands.some(function(slug){
var brand = BRAND_CONFIG.find(function(candidate){ return candidate.slug === slug; });
return brand && item.store[brand.column] === '1';
});
return stateMatch && categoryMatch && brandMatch;
});

window.renderMarkers(filteredMarkers);
updateStats(filteredMarkers);
updateFilterTabBadges();
}

function clearFilter(selector){
document.querySelectorAll(selector).forEach(function(cb){ cb.checked = false; });
applyFilters();
}

document.getElementById('clearStateFilter').addEventListener('click',function(){
clearFilter('.stateCheckbox');
});

document.getElementById('clearCategoryFilter').addEventListener('click',function(){
clearFilter('.categoryCheckbox');
});

document.getElementById('clearBrandFilter').addEventListener('click',function(){
clearFilter('.brandCheckbox');
});

document.addEventListener('change',function(e){
if(
e.target.classList.contains('stateCheckbox') ||
e.target.classList.contains('categoryCheckbox') ||
e.target.classList.contains('brandCheckbox')
){
applyFilters();
}
});

document.getElementById('filterTabs').addEventListener('click',function(e){
var tab = e.target.closest('[data-filter-tab]');
if(tab && !tab.hidden){
setActiveFilterTab(tab.dataset.filterTab,false);
}
});

document.getElementById('filterTabs').addEventListener('keydown',function(e){
if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){
return;
}
var tabs = Array.prototype.filter.call(
document.querySelectorAll('[data-filter-tab]'),
function(tab){ return !tab.hidden; }
);
var index = tabs.indexOf(document.activeElement);
if(index === -1){
return;
}
e.preventDefault();
if(e.key === 'Home'){
index = 0;
}else if(e.key === 'End'){
index = tabs.length - 1;
}else{
index = (index + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
}
setActiveFilterTab(tabs[index].dataset.filterTab,true);
});

renderFilterTabs();
renderStateFilter();
renderCategoryFilter();
renderBrandFilter();
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


def build_page(brands: list[dict[str, str]]) -> str:
    html = SOURCE.read_text(encoding="utf-8")
    html = replace_once(
        html,
        "<title>VPL Germany Network Map</title>",
        "<title>VPL Germany Network Map Preview</title>\n" + PREVIEW_META,
        "title",
    )
    html = replace_once(html, "</style>", PREVIEW_CSS + "\n</style>", "style end")
    html = replace_once(html, "<body>", "<body>\n" + PREVIEW_BADGE, "body start")

    filter_start = html.index('<div id="stateFilterContainer">')
    filter_end = html.index('\n\n</div>\n\n\n</div>\n\n<div id="mapStyleBar">', filter_start)
    html = html[:filter_start] + FILTER_MARKUP + html[filter_end:]

    html = replace_once(
        html,
        "<script>\n\nvar map =",
        "<script>\n\n" + feature_bootstrap(brands) + "var map =",
        "map bootstrap",
    )
    html = replace_once(
        html,
        "'VPL门店地图信息.csv?v=' + Date.now(),",
        "'/preview/data/locations.csv?v=' + Date.now(),",
        "preview CSV path",
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
    filter_logic_end = html.index("\n  \nfetch('/Germany_border_sehr_hoch.geo.json')", filter_logic_start)
    html = html[:filter_logic_start] + FILTER_LOGIC + html[filter_logic_end:]
    return "\n".join(line.rstrip() for line in html.splitlines()) + "\n"


def build_preview() -> None:
    brands = load_brand_config()
    if not CANDIDATE_CSV.is_file():
        raise RuntimeError(f"Candidate CSV is missing: {CANDIDATE_CSV}")

    page = build_page(brands)
    PREVIEW_DIR.mkdir(exist_ok=True)
    PREVIEW_DATA.parent.mkdir(exist_ok=True)
    shutil.copyfile(CANDIDATE_CSV, PREVIEW_DATA)

    source_hash = sha256(CANDIDATE_CSV)
    preview_hash = sha256(PREVIEW_DATA)
    if source_hash != preview_hash:
        raise RuntimeError("Preview CSV copy hash does not match candidate source")
    PREVIEW_DATA_HASH.write_text(
        f"{source_hash}  map data/VPL门店地图信息_20260831_English.csv\n"
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
