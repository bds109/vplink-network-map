from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "index.html"
TARGET_DIR = ROOT / "preview"
TARGET = TARGET_DIR / "index.html"

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

@media (max-width: 768px){
#previewEnvBadge{
top:12px;
right:12px;
font-size:11px;
padding:8px 12px;
}
}
"""


def build_preview() -> None:
    html = SOURCE.read_text(encoding="utf-8")

    html = html.replace(
        "<title>VPL Germany Network Map</title>",
        "<title>VPL Germany Network Map Preview</title>\n" + PREVIEW_META,
        1,
    )
    html = html.replace("</style>", PREVIEW_CSS + "\n</style>", 1)
    html = html.replace("<body>", "<body>\n" + PREVIEW_BADGE, 1)
    html = html.replace(
        "'VPL门店地图信息.csv?v=' + Date.now(),",
        "'../VPL门店地图信息.csv?v=' + Date.now(),",
    )
    html = html.replace(
        "fetch('Germany_border_sehr_hoch.geo.json')",
        "fetch('../Germany_border_sehr_hoch.geo.json')",
    )
    html = html.replace(
        "fetch('2_hoch.geo_1.4M.json')",
        "fetch('../2_hoch.geo_1.4M.json')",
    )

    TARGET_DIR.mkdir(exist_ok=True)
    TARGET.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    build_preview()
