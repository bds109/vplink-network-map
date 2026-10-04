from pathlib import Path

from build_preview import BRAND_CONFIG_SOURCE, CANDIDATE_CSV, ROOT, SOURCE, build_page
from validate_locations import validate_or_exit


def write_page(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def build_production() -> None:
    report = validate_or_exit(CANDIDATE_CSV, config=BRAND_CONFIG_SOURCE, template=SOURCE)
    brands = report["brands"]
    root_page = build_page(brands, preview=False, noindex=False)
    private_page = build_page(brands, preview=False, noindex=True)

    write_page(ROOT / "index.html", root_page)
    targets = (Path("network-overview/index.html"),)
    targets += tuple(Path(brand["slug"]) / "index.html" for brand in brands)
    for relative_target in targets:
        write_page(ROOT / relative_target, private_page)


if __name__ == "__main__":
    build_production()
