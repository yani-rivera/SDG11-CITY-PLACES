# Coffee & Bread: Coffee Places and Bakeries in Urban Centres Worldwide

**Dataset README** · SDG9-COFFEEANDBREAD · made with SDG11-CITY-PLACES v[[VERSION]] (code then named SDG9-COFFEEANDBREAD)
Author: Yanira A. Rivera (ORCID [0000-0003-3309-5256](https://orcid.org/0000-0003-3309-5256))
Run: `[[RUN_ID]]` · Overture Maps release `2026-10-21.0` · accessed [[ACCESS_DATE]]

## What this is

Counts of coffee places and bakeries for each of the 11,422 urban centres in the GHSL Urban
Centre Database (R2024A, epoch 2025), built from the Overture Maps Places theme. It includes
the per-city counts, the individual places inside each city, the full extract, the providers
that reported each place, and an interactive map.

[[N_IN_CITIES]] places fall inside an urban centre ([[N_COFFEE]] coffee, [[N_BAKERY]] bakery);
[[N_CITIES_WITH_PLACES]] of the 11,422 urban centres have at least one.

## SDG framing

**SDG 9 (Industry, Innovation and Infrastructure):** target 9.3 (small-scale enterprises and
their integration into markets) and target 9.c (access to information and communications
technology). Related: 8.3 (micro, small and medium enterprises) and 17.18 (availability of
high-quality, timely data).

## Files

| File | Format | Contents |
|---|---|---|
| `city_counts.csv` | CSV | One row per urban centre: counts, rates, providers |
| `city_sources.csv` | CSV | Places reported per city × group × provider |
| `points_in_cities.parquet` | Parquet | Every coffee place / bakery inside an urban centre, with its city |
| `places.parquet` | Parquet | Full extract worldwide, including places outside urban centres |
| `map.html` | HTML | Interactive map (open in a browser; needs internet for the basemap) |
| `config.yaml` | YAML | Exact configuration of the run |
| `provenance.json` | JSON | Versions, hashes, sources, row counts per step |
| `run.log` | text | Timestamped log of the run |

Parquet files open in QGIS, DuckDB, Python (pandas/pyarrow) or R (arrow). Not in Excel; use
`city_counts.csv` for spreadsheets.

### `city_counts.csv`

| Column | Meaning |
|---|---|
| `city_id` | GHSL urban centre ID (`ID_UC_G0`) |
| `city` | Main name of the urban centre (GHSL `GC_UCN_MAI_2025`) |
| `country` | Country (GHSL `GC_CNT_GAD_2025`) |
| `pop` | Population 2025, GHSL modelled estimate (`GC_POP_TOT_2025`) |
| `cx`, `cy` | A point inside the urban centre, WGS84 lon/lat (for labelling/mapping) |
| `n_coffee`, `n_bakery` | Places in each group inside the urban centre |
| `n_providers` | Number of distinct data providers reporting any place in the city |
| `n_multi_source` | Places reported by 2+ independent providers |
| `coffee_per_10k`, `bakery_per_10k` | Places per 10,000 people |
| `coffee_to_bakery` | Coffee places per bakery (empty when there are no bakeries) |
| `share_multi_source` | `n_multi_source` / all places in the city |

### `city_sources.csv`

| Column | Meaning |
|---|---|
| `city_id` | GHSL urban centre ID |
| `grp` | `coffee` or `bakery` |
| `provider` | Data provider (from Overture `sources[].dataset`) |
| `n` | Places in that city and group reported by that provider |

A place reported by two providers counts once in `city_counts.csv` but once per provider here.

### `points_in_cities.parquet` and `places.parquet`

| Column | Meaning |
|---|---|
| `city_id` | GHSL urban centre ID (`points_in_cities` only) |
| `id` | Overture place ID (GERS) |
| `name` | Primary name |
| `label` | Overture category (`taxonomy.primary`) |
| `brand` | Overture brand name, if any |
| `grp` | `coffee` or `bakery` |
| `matched_by` | `label` (category in the list) or `brand` (brand in the list) |
| `confidence` | Overture existence confidence, 0–1 |
| `datasets` | Providers that reported the place |
| `lon`, `lat` | WGS84, centre of the Overture bounding box |

In `points_in_cities.parquet`, `datasets` excludes Overture's own processing stamps
("Overture", "Overture-signals"); `places.parquet` keeps the raw list.

## Method

1. **Places:** Overture Maps Places, release 2026-10-21.0, read directly from Overture's public
   bucket with DuckDB. Kept when the category is in the lists below, or the brand is in the brand
   list, and `confidence ≥ 0.5`.
   - **coffee:** `cafe`, `coffee_shop`, `coffee_roastery`, `hong_kong_style_cafe`
   - **bakery:** `bakery`, `patisserie_cake_shop`, `bagel_shop`, `flatbread_shop`, `donut_shop`
   - **brands → bakery:** Cinnabon (many stores are labelled fast food or restaurant)
   - **left out on purpose:** `internet_cafe`, `vr_cafe`, `cafeteria` (canteen), `coffee_and_tea_supplies`
   - Lists chosen from a scan of all Overture labels containing coffee/café/bakery/pastry terms.
2. **Cities:** GHSL UCDB R2024A v1.2, layer `GHSL_UCDB_THEME_GENERAL_CHARACTERISTICS_GLOBE_R2024A`,
   reprojected from Mollweide (ESRI:54009) to WGS84.
3. **Join:** each place is assigned to the urban centre polygon that contains it; places outside
   all urban centres are kept only in `places.parquet`.
4. **Providers:** counted from `sources[].dataset`, excluding Overture's own stamps.

## Limitations: please read before using

- **Visibility, not reality.** The data shows places that are visible to the providers behind
  Overture. In many cities, especially in the Global South, a place appears almost only if it has
  a social-media presence: in Tegucigalpa [[TEGUS_META_SHARE]] of the places were reported by Meta
  alone. Small bakeries without an online presence are under-counted. Many urban centres in Africa
  show zero places although coffee and bread are plainly there.
- **Labels, not functions.** A Brazilian *padaria* serves coffee all day but is labelled bakery;
  a café that bakes may be labelled coffee. Colours on the map reflect labels.
- **Places, not visits or consumption.** One busy store counts the same as a quiet one. Much coffee
  is drunk at home (e.g. Honduras, Ethiopia, Finland) and never appears here.
- **Chains are inconsistently branded.** The same chain can appear under several brand names, or
  with no brand tag at all.
- **Confidence filter.** `confidence ≥ 0.5` may drop places reported by a single provider, which
  matters most where data is sparse.
- **Urban centres only.** GHSL urban centres are dense cores; suburbs and towns outside them are
  not counted in `city_counts.csv` (they are in `places.parquet`).
- **Population** is GHSL's modelled 2025 estimate, not a census count.
- **Locations** are the centre of each place's bounding box.

## Reproduce

Code: SDG11-CITY-PLACES [[CODE_DOI]], version [[VERSION]]. With the same Overture release and
GHSL file, `python run.py all` reproduces these files; `provenance.json` records versions and
file hashes. Overture keeps only recent releases online, which is one reason the extracted places
are included here.

## Sources and licences

- **Places:** Overture Maps Foundation, overturemaps.org. Places theme, release 2026-10-21.0,
  accessed [[ACCESS_DATE]]. Data contributed by [[PROVIDERS]]. Provider licences:
  CDLA-Permissive-2.0 (e.g. Meta, Microsoft, BrightQuery), Apache-2.0 (Foursquare), CC0 1.0
  (AllThePlaces). See https://docs.overturemaps.org/attribution/
- **Urban centres and population:** GHSL Urban Centre Database R2024A v1.2, epoch 2025,
  European Commission, Joint Research Centre. Pesaresi, M., Schiavina, M., Politis, P., Freire, S.,
  Krasnodębska, K., Uhl, J. H., … Kemper, T. (2024). Advances on the Global Human Settlement Layer
  by joint assessment of Earth Observation and population survey data. *International Journal of
  Digital Earth*, 17(1). https://doi.org/10.1080/17538947.2024.2390454
- **Basemap (map.html):** © CARTO, © OpenStreetMap contributors.
- **This dataset:** [[LICENCE]]. The redistributed Overture records keep their providers' licences
  listed above.

## How to cite

Rivera, Y. A. (2026). *Coffee & Bread: Coffee Places and Bakeries in Urban Centres Worldwide*
(Overture Maps 2026-10-21.0) [Data set]. Zenodo. [[DATA_DOI]]

## Notes

The processing code was written with AI assistance (Claude, Anthropic); all choices of
categories, sources and checks were reviewed by the author. If you use this dataset, I'd love to
hear about it: [[CONTACT]]
