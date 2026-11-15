# SDG11-CITY-PLACES

**Version 0.8.0** (2026-11-12) · see [CHANGELOG.md](CHANGELOG.md) · check yours with `python run.py --version`

Counts any kind of place in every city of the world, and **who reports it**. Pipeline name:
`city_places`. One config per topic:

| Config | Topic | Status |
|---|---|---|
| `config/coffee_bread.yaml` | coffee places and bakeries | first edition, dataset **SDG9-COFFEEANDBREAD** (made with v0.7.2) |
| `config/bookstores.yaml` | bookshops (and libraries) | provisional labels: run `discover` first |

`find` searches one or more brands or names worldwide (e.g. gyms) without a config of its own.

Until v0.7.4 this code was called SDG9-COFFEEANDBREAD (package `cbc`). The coffee & bread dataset
keeps that name; the code was renamed when it grew beyond coffee and bread.

## SDG framing

**SDG 11: Sustainable Cities and Communities**: the unit is the city (GHSL urban centres), and
the question is what each city offers and how visible it is.
- **11.3** inclusive urbanization and capacity for planning: what services and meeting places a
  city has; **11.7** access to public spaces (libraries, parks) where a topic covers them.

Related: **9.3** and **9.c** (small enterprises; access to information and communications
technology: in data-sparse cities a place enters global data largely through social media, so
digital visibility works as market visibility), **8.3** and **17.18** (availability of
high-quality, timely data).

- **Places:** Overture Maps Places (release set in each config), read straight from the public S3 bucket with DuckDB. Nothing to download.
- **Cities:** GHSL Urban Centre Database R2024A (one consistent city definition, with population).
- **Output:** one row per urban centre (counts and per-10k-people rates per group; coffee:bakery ratio for that topic) and, for coffee & bread, an interactive map.

## Setup (Mac, Apple Silicon)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Download the GHSL UCDB GeoPackage from
https://human-settlement.emergency.copernicus.eu/ghs_ucdb_2024.php
and put it in `data/`.

## Run, in this order

```bash
python run.py inspect-cities   # 1. check layer + field names, fix `cities:` in the config
python run.py discover         # 2. see real category labels with counts, fix `groups:`
python run.py all              # 3. extract + count + map -> outputs/<run_id>/
```

`discover` scans the whole global places table once (a few minutes, a few GB over the network).
`extract` does the same scan but keeps only your labels, so later steps are local and fast.
To recount with a changed city layer without re-downloading:
`python run.py count --run outputs/<run_id>`.
To restyle the map only: `python run.py map --run outputs/<run_id>`. To look at it: `python run.py serve --run outputs/<run_id>`, then open http://127.0.0.1:8000.

To find one brand or name worldwide (any category):

```bash
python run.py find --name "Equinox"               # everything starting with "Equinox"
python run.py find --name "Equinox" --labels gym  # only places labelled gym
python run.py find --name "Equinox,Cyber,Casa Campo,Gold's Gym" --contains --country HN
```

Several names go in one scan, comma-separated; the `search` column says which one matched.
`--contains` also finds the text in the middle of a name, `--country` keeps one country.

It writes `outputs/find/<name>_<time>/places.csv` (name, brand, category, country, locality,
providers, lat/lon), `summary.txt` (matches by category and country) and `provenance.json`.
Run it without `--labels` first: the summary shows what else shares the name.

**Other categories (e.g. bookshops):** `config/bookstores.yaml` runs the same per-city count
for bookshops. Run `python run.py discover --config config/bookstores.yaml`, keep the right
labels under `groups`, then `extract` and `count` with the same `--config`. Results go to
`outputs/bookstores/`; the built-in map is coffee/bakery only, so map them in QGIS.

## Logs: is it running?

Every command prints timestamped `START` / `DONE ... in N s` lines and writes the same to a log file:
- `discover` / `inspect-cities` → `outputs/logs/<command>_<time>.log`
- `extract` / `count` / `map` / `all` → `outputs/<run_id>/run.log`

DuckDB's progress bar is switched on for the long Overture scans. If something fails, the error and
traceback are in the log file too.

## Outputs (per run folder)

| File | What |
|---|---|
| `config.yaml` | exact config used |
| `run.log` | timestamped log of the run |
| `provenance.json` | run id, script version, git commit, config hash, Overture release, GHSL file hash, software versions, row counts per step |
| `places.parquet` | every coffee/bakery point kept (id, name, label, group, confidence, providers, lon, lat) |
| `city_counts.csv` | per city: `n_coffee`, `n_bakery`, `*_per_10k`, `coffee_to_bakery`, `n_providers`, `n_multi_source`, `share_multi_source`, label point `cx`/`cy` |
| `city_sources.csv` | per city x group x provider: how many places each provider reported |
| `points_in_cities.parquet` | the places that fall inside an urban centre, tagged with `city_id` |
| `map/` (or `map.html`) | interactive map; see "The map" (needs internet for the basemap) |

## Who reports the places

Every Overture place lists the data providers that supplied it (`sources[].dataset`: e.g. Meta, Microsoft, Foursquare, AllThePlaces). The pipeline keeps that list per place and adds:

- `n_providers`: how many different providers report anything in the city
- `n_multi_source` / `share_multi_source`: places reported by 2+ providers (more corroborated)
- `city_sources.csv`: the full city x provider breakdown

A place reported by two providers counts once in `n_coffee`/`n_bakery`, but once for each provider in `city_sources.csv`.

## The map

- **Cities** are circles: size = coffee places + bakeries; colour runs from golden (more bakeries) through grey (balanced) to brown (more coffee). Tap or click for counts, per-10k rates and the top providers reporting there.
- **Individual places** appear from zoom 10 (`map.point_minzoom`), brown = coffee, golden = bakery; tap one to see who reported it.
- **Phones:** the legend is a sheet along the bottom (folded at first, the colour bar always shows); taps have a wider hit area. On computers the legend is a small box that folds with the ⌃ button; the page remembers the choice.
- The link keeps the view (`…/index.html#11/14.09/-87.21` opens on Tegucigalpa), so a view can be shared.

### Two ways to build it (`map.mode`)

| mode | output | notes |
|---|---|---|
| `tiled` (default) | `outputs/<run_id>/map/` folder: `index.html`, `data/cities.json`, `data/places/<cell>.json` | All places, no cap. The page loads the city circles (~1 MB), then the places of a grid cell (`map.tile_deg`, 1°) only when you zoom into it. Light on phones. Needs a web server: publish the folder on GitHub Pages, or look at it with `python run.py serve --run outputs/<run_id>`. |
| `single` | `outputs/<run_id>/map.html` | Everything in one file you can double-click. Capped at `map.max_points` (whole cities, largest first); ~50 MB at 1 million places, too heavy for many phones. |

To publish on GitHub Pages, copy the contents of `map/` into the Pages folder of a repository.

Title, colours, basemap and mode are in the `map:` section of the config. The basemap is
[OpenFreeMap](https://openfreemap.org) (no API key). Security measures are described in `SECURITY.md`.

## Things to keep in mind

- **Labels are your choice.** The `groups` in the config were chosen from `discover` output for release 2026-10-21.0; rerun `discover` for a new release.
- **Brands:** the optional `brands:` section adds a brand to a group even when its label differs (e.g. Cinnabon kiosks labeled `fast_food_restaurant`). Matched on Overture's brand field, not the name. Each place records `matched_by` = `label` or `brand`. Overture's `categories` column was removed in the 2026-09-23 release; this uses `taxonomy.primary`.
- **Coverage is uneven.** Overture is commercial-sourced, so counts partly reflect how visible a city is to data providers, not only how many cafés exist.
- **Points outside urban centres are dropped** by design.
- **Attribution:** Overture data carries per-source attribution requirements; check the Overture docs before publishing.

## Publishing the dataset

`docs/DATA_README.md` (goes into the Zenodo dataset record) and `docs/ZENODO_DESCRIPTION.md`
(metadata to paste) are drafts with `[[PLACEHOLDERS]]`. Fill them with
`python run.py stats --run outputs/<run_id>`.

## Citing the sources

- **GHSL Urban Centre Database:** Pesaresi, M., Schiavina, M., Politis, P., Freire, S., Krasnodębska, K., Uhl, J. H., … Kemper, T. (2024). Advances on the Global Human Settlement Layer by joint assessment of Earth Observation and population survey data. *International Journal of Digital Earth*, 17(1). https://doi.org/10.1080/17538947.2024.2390454
- **Overture Maps Places:** cite the release used (in `provenance.json`) and follow Overture's attribution guidance.

The GHSL citation and version are also stored in `config.yaml` and copied into every run's `provenance.json`.

## Structure

```
config/coffee_bread.yaml  coffee & bread (first edition)
config/bookstores.yaml    bookshops (provisional)
run.py               CLI
cityplaces/config.py        load + validate config
cityplaces/db.py            DuckDB connection (spatial, httpfs)
cityplaces/provenance.py    run folder + provenance.json
cityplaces/log.py           screen + file logging, step timers
cityplaces/discover.py      candidate labels
cityplaces/places.py        Overture extract
cityplaces/cities.py        GHSL load + reproject
cityplaces/count.py         point-in-polygon counts
cityplaces/mapviz.py        builds the map (tiled folder or single file)
cityplaces/mapdata.py       queries for the map: cities, providers, places, grid cells
cityplaces/mapsafe.py       pinned MapLibre + integrity hashes, URL checks, safe JSON, CSP
cityplaces/map_template.html  map page (MapLibre)
SECURITY.md                 how the map page is protected
cityplaces/find.py      find brands/names worldwide
cityplaces/stats.py     numbers for the dataset README
docs/coffee_bread/      dataset README + Zenodo text for the first edition
```
