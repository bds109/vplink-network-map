import json
from pathlib import Path

from build_preview import BRAND_CONFIG_SOURCE, CANDIDATE_CSV, GALLERY_CONFIG_SOURCE, ROOT, SOURCE, build_page
from validate_locations import validate_or_exit


def write_page(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def build_production() -> None:
    report = validate_or_exit(CANDIDATE_CSV, config=BRAND_CONFIG_SOURCE, template=SOURCE)
    brands = report["brands"]
    root_page = build_page(brands, preview=False, noindex=False)
    private_page = build_page(brands, preview=False, noindex=True)

    gallery_config = json.loads(GALLERY_CONFIG_SOURCE.read_text(encoding="utf-8"))
    full_config = json.dumps(gallery_config, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    preview_guard = """    (config.url.startsWith('https://gallery.vpl-gmbh.com/') ||
      (location.pathname.startsWith('/preview/') &&
       config.url==='https://vplink-performance-preview-20261024.steve-zhou.workers.dev/overview')));"""
    production_guard = "    config.url.startsWith('https://gallery.vpl-gmbh.com/'));"
    targets = [(Path("index.html"), root_page, None),
               (Path("network-overview/index.html"), private_page, "overview")]
    targets += [(Path(brand["slug"]) / "index.html", private_page, brand["slug"]) for brand in brands]
    for relative_target, page, scope in targets:
        # Match the accepted Preview's route scoping, without its URL exception.
        scoped = {"performanceGallery": {
            key: entry if key == scope else {"url": None, "status": "not-configured"}
            for key, entry in gallery_config["performanceGallery"].items()
        }}
        scoped_config = json.dumps(scoped, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        config_line = "var STORE_GALLERY_CONFIG = " + full_config + ";"
        if page.count(config_line) != 1 or page.count(preview_guard) != 1:
            raise ValueError("Production Gallery config/guard baseline mismatch")
        page = page.replace(config_line, "var STORE_GALLERY_CONFIG = " + scoped_config + ";")
        page = page.replace(preview_guard, production_guard)
        if "workers.dev" in page:
            raise ValueError("Production page must not reference Preview Workers")
        write_page(ROOT / relative_target, page)


if __name__ == "__main__":
    build_production()
