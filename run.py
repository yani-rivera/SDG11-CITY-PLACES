"""CLI for SDG11-CITY-PLACES (pipeline: city_places).

    python run.py discover                 # list candidate category labels + counts
    python run.py inspect-cities           # list GHSL layers/fields
    python run.py extract                  # Overture -> places.parquet (new run folder)
    python run.py count --run outputs/<id> # cities x places -> city_counts.csv
    python run.py map --run outputs/<id>   # city_counts + points -> map/ (or map.html)
    python run.py serve --run outputs/<id> # look at the map at http://127.0.0.1:8000
    python run.py all                      # extract + count + map in one run
    python run.py stats --run outputs/<id> # numbers for the dataset README / Zenodo text
    python run.py find --name "Equinox"    # every place of one or more brands/names worldwide

Every command logs timestamped messages to the screen and to a log file:
outputs/logs/<command>_<time>.log, or outputs/<run_id>/run.log for runs.
"""
import argparse
from datetime import datetime
from pathlib import Path

from cityplaces import __version__, __project__
from cityplaces.config import load_config, overture_glob
from cityplaces.db import connect
from cityplaces.log import setup_logging, timed
from cityplaces.provenance import Run
from cityplaces import discover, places, cities, count, mapviz, stats, find


def cmd_discover(cfg, log):
    log.info("Scanning Overture %s for candidate labels. Takes several minutes; "
             "a progress bar may appear.", cfg["overture"]["release"])
    log.info("source: %s", overture_glob(cfg))
    with timed("discover"):
        con = connect(cfg["overture"]["s3_region"])
        df = discover.discover_labels(con, cfg)
    print(df.to_string(index=False))
    out = Path(cfg["run"]["output_dir"]) / f"discover_{cfg['overture']['release']}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    log.info("%d labels found, saved %s. Edit `groups` in the config, then run `extract`.", len(df), out)


def cmd_inspect_cities(cfg, log):
    log.info("Reading layers/fields of %s", cfg["cities"]["path"])
    with timed("inspect-cities"):
        con = connect()
        summary, ok = cities.inspect_cities(con, cfg)
    print(summary)
    out = Path(cfg["run"]["output_dir"]) / "logs" / "cities_fields.txt"
    out.write_text(summary, encoding="utf-8")
    if ok:
        log.info("Saved %s. The layer and fields in `cities:` match the file: ready for `cities`.", out)
    else:
        log.warning("Saved %s. Fix `cities:` in the config where it says NOT FOUND.", out)


def cmd_find(cfg, log, names, labels, contains, country):
    log.info("Searching Overture %s for %s (global scan, several minutes)",
             cfg["overture"]["release"], ", ".join(names))
    with timed("find"):
        con = connect(cfg["overture"]["s3_region"])
        info = find.find_places(con, cfg, names, labels, contains, country)
    print(info["summary"])
    log.info("%d matches. Saved %s (places.csv, summary.txt, provenance.json).", info["matches"], info["dir"])


def step_extract(cfg, run, log):
    log.info("Extracting %s from Overture %s (global scan, several minutes)",
             ", ".join(cfg["groups"]), cfg["overture"]["release"])
    with timed("extract"):
        con = connect(cfg["overture"]["s3_region"])
        out = run.dir / "places.parquet"
        info = places.extract_places(con, cfg, out)
    run.log_step("extract", output=out.name, **info)
    log.info("extract: %s", info["rows_by_group"])


def step_count(cfg, run, log):
    with timed("load cities"):
        con = connect()
        n = cities.load_cities(con, cfg)
    log.info("%d urban centres loaded", n)
    with timed("count"):
        out = run.dir / "city_counts.csv"
        pts = run.dir / "points_in_cities.parquet"
        info = count.count_per_city(con, cfg, run.dir / "places.parquet", out, pts)
    run.log_step("count", outputs=[out.name, pts.name], cities_loaded=n, **info)
    log.info("count: %s", info)


def step_map(cfg, run, log):
    import duckdb
    with timed("map"):
        info = mapviz.build_map(duckdb.connect(), cfg, run.dir)
    run.log_step("map", **info)
    log.info("map: %s", info)


def cmd_serve(run_dir: Path, port: int):
    """Serve the run's map folder on this computer only (127.0.0.1)."""
    import functools
    import http.server
    folder = run_dir / "map"
    if not (folder / "index.html").exists():
        raise SystemExit(f"No {folder}/index.html. Build it first: python run.py map --run {run_dir}")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as srv:
        print(f"Map at http://127.0.0.1:{port}/  (Ctrl+C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    ap = argparse.ArgumentParser(description=f"{__project__} (city_places) v{__version__}")
    ap.add_argument("--version", action="version", version=f"{__project__} {__version__}")
    ap.add_argument("command", choices=["discover", "inspect-cities", "extract", "count", "map", "all", "stats", "find", "serve"])
    ap.add_argument("--config", default="config/coffee_bread.yaml")
    ap.add_argument("--run", help="existing run folder (for `count`, `map`, `stats` or `serve`)")
    ap.add_argument("--port", type=int, default=8000, help="for `serve`: port on this computer (default 8000)")
    ap.add_argument("--name", help='for `find`: one or more names, comma-separated, e.g. "Equinox,Gold\'s Gym"')
    ap.add_argument("--contains", action="store_true", help="for `find`: match the text anywhere in the name, not only at the start")
    ap.add_argument("--country", help="for `find`: two-letter country code, e.g. HN")
    ap.add_argument("--labels", help="for `find`: optional comma-separated category labels to keep, e.g. gym")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.command == "find":
        if not args.name:
            ap.error('find needs --name, e.g. --name "Equinox"')
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        log = setup_logging(Path(cfg["run"]["output_dir"]) / "logs" / f"find_{stamp}.log")
        log.info("%s v%s  command=find  name=%s", __project__, __version__, args.name)
        names = [x.strip() for x in args.name.split(",") if x.strip()]
        labels = [x.strip() for x in args.labels.split(",")] if args.labels else None
        return cmd_find(cfg, log, names, labels, args.contains, args.country)

    if args.command in ("discover", "inspect-cities"):
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        log = setup_logging(Path(cfg["run"]["output_dir"]) / "logs" / f"{args.command}_{stamp}.log")
        log.info("%s v%s  command=%s", __project__, __version__, args.command)
        fn = cmd_discover if args.command == "discover" else cmd_inspect_cities
        return fn(cfg, log)

    if args.command == "serve":
        if not args.run:
            ap.error("serve needs --run outputs/<run_id>")
        return cmd_serve(Path(args.run), args.port)

    if args.command == "stats":
        if not args.run:
            ap.error("stats needs --run outputs/<run_id>")
        import duckdb
        for k, v in stats.run_stats(duckdb.connect(), Path(args.run)).items():
            print(f"[[{k}]]  {v}")
        return

    run = Run(cfg, args.run) if args.run else Run(cfg)
    log = setup_logging(run.dir / "run.log")
    log.info("%s v%s  command=%s  run=%s", __project__, __version__, args.command, run.dir)
    if args.command in ("extract", "all"):
        step_extract(cfg, run, log)
    if args.command in ("count", "all"):
        step_count(cfg, run, log)
    if args.command in ("map", "all"):
        if {"coffee", "bakery"} <= set(cfg["groups"]):
            step_map(cfg, run, log)
        else:
            log.warning("map skipped: the built-in map draws coffee and bakery groups only. "
                        "Use city_counts.csv and points_in_cities.parquet in QGIS.")
    log.info("Finished. Run folder: %s", run.dir)


if __name__ == "__main__":
    main()
