"""Build the interactive map.

map.mode: tiled (default)  -> <run>/map/index.html + data/cities.json + data/places/<cell>.json
          single           -> <run>/map.html, everything inside one file (capped at map.max_points)

Tiled is light enough for phones: the page loads the 11k city circles, and the individual places
of one grid cell only when the reader zooms into it. It must be opened through a web server
(GitHub Pages, or `python run.py serve --run outputs/<id>`), not by double-clicking the file.
"""
import hashlib
import re
import shutil
from html import escape as html_escape
from pathlib import Path

from . import mapdata
from .mapsafe import MAPLIBRE, csp, origin, safe_url, to_json

TEMPLATE = Path(__file__).with_name("map_template.html")

DEFAULTS = {
    "mode": "tiled",
    "tile_deg": 1,
    "max_points": 1000000,          # single mode only
    "point_minzoom": 10,
    "basemap": "https://tiles.openfreemap.org/styles/positron",
    "basemap_attribution": "OpenFreeMap © OpenMapTiles, data from OpenStreetMap contributors",
    "basemap_origins": None,        # servers the basemap loads from; default: the style's own server
    "tagline": "",
    "credit": "",
}


def map_settings(cfg: dict) -> dict:
    m = {**DEFAULTS, **{k: v for k, v in cfg["map"].items() if v is not None}}
    if m["mode"] not in ("tiled", "single"):
        raise ValueError("map.mode must be 'tiled' or 'single'")
    if not safe_url(m["basemap"], https_only=True):
        raise ValueError("map.basemap must be an https URL")
    if not 0.25 <= float(m["tile_deg"]) <= 10:
        raise ValueError("map.tile_deg must be between 0.25 and 10 degrees")
    origins = m["basemap_origins"] or [origin(m["basemap"])]
    bad = [o for o in origins if not safe_url(o, https_only=True)]
    if bad:
        raise ValueError(f"map.basemap_origins must be https URLs: {bad}")
    m["basemap_origins"] = [origin(o) for o in origins]
    for k in ("coffee", "bakery"):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(m["colors"][k])):
            raise ValueError(f"map.colors.{k} must be a hex colour like #5b3a29")
    return m


def _link(text: str, url: str) -> str:
    """A link only for plain http(s) URLs; anything else is shown as text."""
    ok = safe_url(url)
    if not ok:
        return html_escape(text)
    return f'<a href="{html_escape(ok)}" target="_blank" rel="noopener noreferrer">{html_escape(text)}</a>'


def _sources_html(cfg: dict, m: dict, providers: list, run_dir: Path, partial: bool) -> str:
    from . import __version__, __project__
    o, c = cfg["overture"], cfg["cities"]
    e = html_escape
    rid = run_dir.name  # run ids start with YYYYMMDD
    accessed = f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}" if rid[:8].isdigit() else rid
    items = [
        "<b>Places:</b> " + _link("Overture Maps Foundation", "https://overturemaps.org")
        + f", Places theme, release {e(o['release'])}, accessed {e(accessed)}"
        + (f"; data contributed by {e(', '.join(providers))}" if providers else "")
        + ". Provider licences (CDLA-Permissive-2.0, Apache-2.0, CC0): "
        + _link("Overture attribution", "https://docs.overturemaps.org/attribution/") + ".",
        "<b>Cities &amp; population:</b> GHSL Urban Centre Database"
        + (f" {e(c['version'])}" if c.get("version") else "") + ". "
        + _link("Pesaresi et al. (2024)", "https://doi.org/10.1080/17538947.2024.2390454") + ".",
        f"<b>Basemap:</b> {e(m['basemap_attribution'])}",
        f"Built with {e(__project__)} v{e(__version__)}, run {e(run_dir.name)}."
        + (" Individual places shown for the largest cities only." if partial else ""),
    ]
    if m.get("credit"):
        items.append(e(m["credit"]))
    return "".join(f"<li>{x}</li>" for x in items)


def _page(cfg, m, run_dir, settings, providers, partial, embedded: dict) -> str:
    blocks = "\n".join(f'<script type="application/json" id="d-{k}">{to_json(v)}</script>'
                       for k, v in embedded.items())
    values = {
        "__TITLE__": html_escape(m["title"]),
        "__TAGLINE__": (f'<p class="tagline">{html_escape(m["tagline"])}</p>' if m.get("tagline") else ""),
        "__SOURCES__": _sources_html(cfg, m, providers, run_dir, partial),
        "__COFFEE__": m["colors"]["coffee"],
        "__BAKERY__": m["colors"]["bakery"],
        "__ML_JS__": MAPLIBRE["js"], "__ML_JS_SRI__": MAPLIBRE["js_sri"],
        "__ML_CSS__": MAPLIBRE["css"], "__ML_CSS_SRI__": MAPLIBRE["css_sri"],
        "__DATA__": blocks,
        "__SETTINGS__": to_json(settings),
    }
    pattern = re.compile("|".join(re.escape(k) for k in values))
    # one pass, so text inside the data (place names) is never treated as a placeholder
    html = pattern.sub(lambda mt: values[mt.group(0)], TEMPLATE.read_text(encoding="utf-8"))
    return html.replace("__CSP__", html_escape(csp(html, m["basemap_origins"])), 1)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_map(con, cfg: dict, run_dir: Path) -> dict:
    m = map_settings(cfg)
    csv_path = run_dir / "city_counts.csv"
    points_path = run_dir / "points_in_cities.parquet"
    src_csv = run_dir / "city_sources.csv"
    tiled = m["mode"] == "tiled"

    city_rows = mapdata.cities(con, csv_path)
    city_src = mapdata.city_sources(con, src_csv)
    points, providers, info = mapdata.places(con, csv_path, points_path,
                                             None if tiled else m["max_points"])
    partial = info["points_on_map"] < info["points_total"]
    settings = {
        "title": m["title"], "basemap": m["basemap"], "pointMinZoom": m["point_minzoom"],
        "colors": m["colors"], "tiled": tiled, "tileDeg": m["tile_deg"],
        "release": cfg["overture"]["release"], "runId": run_dir.name, "partial": partial,
    }
    provider_list = mapdata.provider_order(con, src_csv)
    info["mode"] = m["mode"]

    if not tiled:
        html = _page(cfg, m, run_dir, settings, provider_list, partial, {
            "cities": {"cities": city_rows, "citySrc": city_src, "providers": providers},
            "points": points,
        })
        out = run_dir / "map.html"
        out.write_text(html, encoding="utf-8")
        info.update(output=out.name, size_mb=round(out.stat().st_size / 1e6, 1), sha256=_sha(out))
        return info

    out_dir = run_dir / "map"
    if out_dir.exists():
        shutil.rmtree(out_dir)            # rebuilt from scratch: no stale cells left behind
    (out_dir / "data" / "places").mkdir(parents=True)
    tiles = mapdata.split_tiles(points, float(m["tile_deg"]))
    for key, pts in tiles.items():
        (out_dir / "data" / "places" / f"{key}.json").write_text(to_json(pts), encoding="utf-8")
    cities_json = out_dir / "data" / "cities.json"
    cities_json.write_text(to_json({
        "cities": city_rows, "citySrc": city_src, "providers": providers,
        "tiles": {k: len(v) for k, v in sorted(tiles.items())},
    }), encoding="utf-8")
    page = out_dir / "index.html"
    page.write_text(_page(cfg, m, run_dir, settings, provider_list, partial, {}), encoding="utf-8")

    sizes = [p.stat().st_size for p in (out_dir / "data" / "places").glob("*.json")]
    info.update(
        output=f"{out_dir.name}/index.html", tiles=len(tiles),
        largest_tile_kb=round(max(sizes, default=0) / 1e3, 1),
        cities_json_mb=round(cities_json.stat().st_size / 1e6, 2),
        size_mb=round((sum(sizes) + cities_json.stat().st_size + page.stat().st_size) / 1e6, 1),
        sha256={"index.html": _sha(page), "data/cities.json": _sha(cities_json)},
    )
    return info
