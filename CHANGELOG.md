# Changelog

The version lives in one place: `cityplaces/__init__.py` (`__version__`).
It is printed by `python run.py --version`, in the first line of every log,
and stored as `script_version` in every run's `provenance.json`.

## 0.9.0 — 2026-11-14
- **Map for phones.** New default `map.mode: tiled` writes `outputs/<run_id>/map/` (index.html,
  cities.json, one small file per 1° grid cell). The page loads places only where the reader zooms
  in, so every place is included (no 1-million cap) and phones no longer have to load ~50 MB.
  `map.mode: single` keeps the one-file map.html.
- **Legend box** is narrower and folds (⌃); on phones it is a bottom sheet, folded at first, with the
  colour bar always visible. The world view opens framed beside the box. Wider tap targets, nearest
  place wins, bigger popup close button, the link keeps the view (`#zoom/lat/lon`).
- **Security:** Content-Security-Policy with a hash for the inline script; MapLibre pinned with
  Subresource Integrity; links and basemap URLs checked; colours validated. See `SECURITY.md`.
- **Basemap:** CARTO → OpenFreeMap (no API key).
- New `python run.py serve --run outputs/<id>` to look at the tiled map on this computer.
- Code split: `mapdata.py` (queries), `mapsafe.py` (security), `mapviz.py` (build).
- No change to counts or tables.

## 0.8.0 — 2026-11-12
- **Renamed** from SDG9-COFFEEANDBREAD to **SDG11-CITY-PLACES**: the code now counts any kind of
  place per city (coffee & bread, bookshops, …). Package `cbc` → `cityplaces`, pipeline name
  `cafe_bakery_cities` → `city_places` (in logs and `provenance.json`).
- `config/config.yaml` → `config/coffee_bread.yaml` (still the default `--config`).
- Dataset docs moved to `docs/coffee_bread/`; they now cite the code as SDG11-CITY-PLACES.
  The coffee & bread dataset keeps its name SDG9-COFFEEANDBREAD (made with v0.7.2).
- No change to results: same queries, same outputs.

Entries below are from when the code was called SDG9-COFFEEANDBREAD.

## 0.7.4 — 2026-11-12
- `find`: several names in one scan (`--name "Equinox,Cyber,Casa Campo,Gold's Gym"`), a
  `search` column saying which name matched, `--contains` to match inside names
  ("Gimnasio Cyber"), and `--country HN`.
- New `config/bookstores.yaml`: the same per-city pipeline for bookshops (provisional labels;
  run `discover` first). `all` skips the built-in map when the groups are not coffee/bakery.

## 0.7.3 — 2026-11-12
- New `find` command: every Overture place whose brand or name starts with a text, worldwide
  (`python run.py find --name "Equinox"`, optional `--labels gym`). Keeps all matches with
  category, country, locality and providers; writes `outputs/find/<name>_<time>/places.csv`,
  `summary.txt` and `provenance.json` (script version, release, search, output SHA-256).

## 0.7.2 — 2026-11-12
- `inspect-cities` checks field names only on the layer the config reads (`cities.layer`),
  marks the other layers "(not used)", and says when everything matches. Before, the
  centroid layer showed NOT FOUND for fields it never needed.

## 0.7.1 — 2026-11-05
- Provenance: every step now records the `script_version`, `git_commit` and `config_sha256`
  that actually ran it. Before, a step rerun on an existing run folder (`count --run`,
  `map --run`) inherited the version recorded when the folder was created.
- New `stats --run outputs/<id>` command: prints the values for the [[PLACEHOLDERS]] in the
  dataset docs (counts, providers, access date, versions, Tegucigalpa Meta-only share).
- New `docs/DATA_README.md` (dataset README: files, columns, method, limitations, sources,
  licences, citation) and `docs/ZENODO_DESCRIPTION.md` (draft Zenodo metadata).

## 0.7.0 — 2026-11-05
- Project named **SDG9-COFFEEANDBREAD** (SDG 9: targets 9.3 and 9.c; related 8.3, 17.18).
  `__project__` in `cbc/__init__.py`; shown by `--version`, in logs, in `provenance.json`
  (`"project"`), and in the map's Sources block. Pipeline/package names unchanged.

## 0.6.4 — 2026-11-05
- Map: optional `map.tagline` shown under the title (empty by default). The interactive map is
  an exploration tool and is not tagged as a #30DayMapChallenge entry: challenge maps are
  made by hand, without AI.

## 0.6.3 — 2026-11-05
- Map: full **Sources** block (collapsible) — Overture Maps Foundation, overturemaps.org, Places
  release + access date + the providers that actually contributed, provider licences and link to
  Overture's attribution page; GHSL UCDB version + Pesaresi et al. (2024) DOI; basemap credit;
  pipeline version and run id. Optional `map.credit` line.
- Config: `map.basemap_attribution`, `map.credit`; `exclude_providers` now also lists
  "Overture-signals" (not in Overture's published provider list); `cities.layer` set to
  GHSL_UCDB_THEME_GENERAL_CHARACTERISTICS_GLOBE_R2024A.

## 0.6.2 — 2026-11-05
- Fix: "Overture" (Overture's own processing stamp in `sources[].dataset`) was counted as a
  provider on every place, so `n_multi_source` / `share_multi_source` were inflated (every
  place looked confirmed by 2+ providers) and `city_sources.csv` had an "Overture" row.
  New config `overture.exclude_providers: ["Overture"]`, applied in the count step.
  Rerun `count` and `map` on an existing run; no new extract needed.

## 0.6.1 — 2026-11-05
- Fix: blank map in Safari ("RangeError: Maximum call stack size exceeded"). Map data is now
  stored as JSON text blocks and read with `JSON.parse` instead of a million-entry JavaScript
  literal. Tested with 1,000,000 points.
- Title, legend and source note are written into the page directly, so they show even if
  the map fails; a status line reports loading progress or any error.
- Strict JSON (NaN/inf → null); single-pass placeholder filling so place names can't
  collide with template placeholders.

## 0.6.0 — 2026-11-05
- Faster extract: the label/brand filter is written as constant IN-lists so DuckDB applies it
  while scanning and reads names/providers only for kept rows (0.5.x read every column of
  every place before filtering: ~1.5 h on a home connection).
- Faster count: the city join is a single `ST_Contains` predicate so DuckDB spatial runs it
  as an R-tree SPATIAL_JOIN instead of comparing every place with every city.
- Outputs unchanged.

## 0.5.1 — 2026-11-05
- `inspect-cities` prints a short summary (layers, feature counts, geometry, field names)
  and checks the `cities:` field names in the config (OK / NOT FOUND); saved to
  `outputs/logs/cities_fields.txt`.
- `--version` flag; this changelog.

## 0.5.0 — 2026-11-05
- Final groups from `discover` (Overture 2026-10-21.0): coffee = cafe, coffee_shop,
  coffee_roastery, hong_kong_style_cafe; bakery = bakery, patisserie_cake_shop,
  bagel_shop, flatbread_shop, donut_shop.
- Optional `brands:` section (matched on `brand.names.primary`); Cinnabon → bakery.
  Each place records `matched_by` = label | brand.

## 0.4.0 — 2026-11-05
- Timestamped logging to screen and file (`outputs/logs/`, `<run>/run.log`), step timers.
- DuckDB progress bar for long scans.

## 0.3.0 — 2026-11-05
- Provider breakdown: `datasets` per place, `n_providers`, `n_multi_source`,
  `share_multi_source`, `city_sources.csv`; providers shown on the map.
- GHSL citation and version recorded in config and provenance.
- Requires DuckDB ≥ 1.3 (new lambda syntax).

## 0.2.0 — 2026-11-05
- Interactive map (`map.html`): cities sized by places, coloured by coffee/bakery balance;
  individual places from zoom 10; points capped by whole cities (`map.max_points`).

## 0.1.0 — 2026-11-05
- First version: Overture Places extract, GHSL urban-centre counts, per-10k rates,
  coffee:bakery ratio, provenance per run.
