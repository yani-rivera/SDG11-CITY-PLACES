# Zenodo record: draft metadata

## Title
Coffee & Bread: Coffee Places and Bakeries in Urban Centres Worldwide (Overture Maps 2026-10-21.0)

## Resource type
Dataset

## Creator
Rivera, Yanira A. (ORCID 0000-0003-3309-5256)

## Description (paste into the Description field)

How many coffee places and bakeries does each city in the world have, and who reports them?

This dataset counts coffee places and bakeries in each of the 11,422 urban centres of the GHSL
Urban Centre Database (R2024A, epoch 2025), using the Overture Maps Places theme (release
2026-10-21.0). [[N_IN_CITIES]] places fall inside an urban centre ([[N_COFFEE]] coffee places and
[[N_BAKERY]] bakeries).

For every urban centre it provides counts, places per 10,000 people, the coffee-to-bakery ratio,
and which data providers reported the places. It also includes every individual place inside a
city, the full worldwide extract, and an interactive map.

The provider breakdown makes a second story visible: where places are seen. In many cities a café
or bakery appears in global data almost only through its social-media presence (in Tegucigalpa,
[[TEGUS_META_SHARE]] were reported by Meta alone), while elsewhere business registries add
a second route. The dataset is therefore as much about the digital visibility of small food
businesses as about coffee and bread.

**Files:** city_counts.csv (one row per urban centre), city_sources.csv (providers per city),
points_in_cities.parquet (places inside urban centres), places.parquet (full extract),
map.html (interactive map), config.yaml, provenance.json and run.log (how it was made).
See DATA_README.md for columns, method and limitations.

**Main limitations:** counts reflect what data providers see, not what exists; labels decide
coffee vs. bakery (e.g. Brazilian padarias count as bakeries); places are counted, not visits;
coffee drunk at home is invisible here.

**SDG:** 9.3 and 9.c (related: 8.3, 17.18).

**Sources:** Overture Maps Foundation, overturemaps.org (Places theme, release 2026-10-21.0,
accessed [[ACCESS_DATE]]); GHSL Urban Centre Database R2024A v1.2, European Commission JRC
(Pesaresi et al., 2024, https://doi.org/10.1080/17538947.2024.2390454).

The processing code was written with AI assistance (Claude, Anthropic) and is published
separately (see related works).

## Keywords
coffee; bakeries; cafés; points of interest; POI; Overture Maps; GHSL; urban centres; cities;
small businesses; digital visibility; data coverage; SDG 9; open data

## Licence
[[LICENCE]] — suggestion: CC BY 4.0 for the derived tables, with a note that redistributed
Overture records keep their providers' licences (CDLA-Permissive-2.0, Apache-2.0, CC0).

## Related works
- **Is supplemented by** → code record (SDG11-CITY-PLACES, Zenodo software DOI) [[CODE_DOI]]
- **References** → https://doi.org/10.1080/17538947.2024.2390454 (GHSL, Pesaresi et al. 2024)
- **References** → https://overturemaps.org (Overture Maps Foundation)

## Version
v[[VERSION]] (pipeline version used for the run)

## Dates
Collected: [[ACCESS_DATE]] (Overture accessed)
