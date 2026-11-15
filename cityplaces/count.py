"""Point-in-polygon join, per-city counts, providers, and the points that fall inside cities."""
from pathlib import Path


def _excluded_list(cfg: dict) -> str:
    """SQL list literal of provider names that are not real data providers."""
    names = (cfg.get("overture") or {}).get("exclude_providers") or []
    return "[" + ", ".join("'" + n.replace("'", "''") + "'" for n in names) + "]::VARCHAR[]"


def join_points(con, places_path, cfg: dict | None = None) -> int:
    """Tag every place with the urban centre it falls in (places outside are dropped).

    The join condition is a single spatial predicate so DuckDB's spatial extension
    can run it as a SPATIAL_JOIN (R-tree), instead of comparing every place with
    every city. Provider names listed in `overture.exclude_providers` (e.g. Overture's
    own processing stamp) are removed from each place's `datasets` here.
    """
    excl = _excluded_list(cfg or {})
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE pts AS
        SELECT * REPLACE (list_filter(datasets, lambda d: NOT list_contains({excl}, d)) AS datasets),
               ST_Point(lon, lat) AS pt
        FROM read_parquet('{places_path}')
    """)
    con.execute("""
        CREATE OR REPLACE TABLE hits AS
        SELECT c.city_id, p.id, p.name, p.label, p.brand, p.grp, p.matched_by,
               p.confidence, p.datasets, p.lon, p.lat
        FROM pts p JOIN cities c ON ST_Contains(c.geom, p.pt)
    """)
    return con.execute("SELECT count(*) FROM hits").fetchone()[0]


def count_per_city(con, cfg: dict, places_path, out_csv, out_points) -> dict:
    groups = list(cfg["groups"].keys())
    n_hits = join_points(con, places_path, cfg)

    count_cols = ",\n".join(
        f"count(DISTINCT h.id) FILTER (WHERE h.grp = '{g}') AS n_{g}" for g in groups
    )
    per10k = ",\n".join(
        f"round(n_{g} / nullif(pop, 0) * 1e4, 3) AS {g}_per_10k" for g in groups
    )
    ratio = ""
    if {"coffee", "bakery"} <= set(groups):
        ratio = ",\n round(n_coffee / nullif(n_bakery, 0), 3) AS coffee_to_bakery"

    con.execute(f"""
        CREATE OR REPLACE TABLE city_counts AS
        WITH agg AS (
            SELECT c.city_id, c.city, c.country, c.pop, c.cx, c.cy,
                   {count_cols},
                   -- reporting: how many providers, and how many places 2+ providers agree on
                   count(DISTINCT d.ds)                                    AS n_providers,
                   count(DISTINCT h.id) FILTER (WHERE len(h.datasets) >= 2) AS n_multi_source
            FROM cities c
            LEFT JOIN hits h USING (city_id)
            LEFT JOIN (SELECT id, unnest(datasets) AS ds FROM hits) d ON d.id = h.id
            GROUP BY ALL
        )
        SELECT *, {per10k}{ratio},
               round(n_multi_source / nullif({' + '.join('n_'+g for g in groups)}, 0), 3) AS share_multi_source
        FROM agg
        ORDER BY pop DESC
    """)
    # long table: one row per city x group x provider
    con.execute("""
        CREATE OR REPLACE TABLE city_sources AS
        SELECT city_id, grp, ds AS provider, count(*) AS n
        FROM (SELECT city_id, grp, unnest(datasets) AS ds FROM hits)
        GROUP BY ALL
        ORDER BY city_id, n DESC
    """)
    out_sources = Path(out_csv).with_name("city_sources.csv")
    con.execute(f"COPY city_counts TO '{out_csv}' (HEADER, DELIMITER ',')")
    con.execute(f"COPY city_sources TO '{out_sources}' (HEADER, DELIMITER ',')")
    con.execute(f"COPY hits TO '{out_points}' (FORMAT parquet, COMPRESSION zstd)")

    n_cities, n_with = con.execute(
        f"SELECT count(*), count(*) FILTER (WHERE {' + '.join('n_'+g for g in groups)} > 0) FROM city_counts"
    ).fetchone()
    providers = dict(con.execute(
        "SELECT provider, sum(n)::BIGINT FROM city_sources GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall())
    return {"cities": n_cities, "cities_with_any_place": n_with,
            "points_in_cities": n_hits, "reports_by_provider": providers,
            "extra_output": out_sources.name}
