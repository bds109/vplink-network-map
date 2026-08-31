from pathlib import Path

from build_preview import ROOT, build_page, load_brand_config


def write_page(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def build_production() -> None:
    brands = load_brand_config()
    root_page = build_page(brands, preview=False, noindex=False)
    private_page = build_page(brands, preview=False, noindex=True)

    write_page(ROOT / "index.html", root_page)
    for relative_target in (
        Path("network-overview/index.html"),
        Path("geekbar/index.html"),
        Path("dojo/index.html"),
    ):
        write_page(ROOT / relative_target, private_page)


if __name__ == "__main__":
    build_production()
