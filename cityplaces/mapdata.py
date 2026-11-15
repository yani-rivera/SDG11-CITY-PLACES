"""Queries that feed the map: city circles, top providers per city, individual places."""
import math


def cities(con, csv_path) -> list:
    """[id, city, country, pop, lon, lat, n_coffee, n_bakery, coffee_per_10k, bakery_per_10k],
    smallest first so big circles are drawn on top."""
    rows = con.execute(f"""
        SELECT city_id, city, country, pop, cx, cy,
               n_coffee, n_bakery, coffee_per_10k, bakery_per_10k
        FROM read_csv_auto('{csv_path}')
        WHERE cx IS NOT NULL
        ORDER BY n_coffee + n_bakery ASC
    """).fetchall()
    return [
        [str(r[0]), r[1], r[2], round(r[3] or 0), round(r[4], 4), round(r[5], 4),
         int(r[6]), int(r[7]), r[8], r[9]]
        for r in rows
    ]


def city_sources(con, sources_csv, top: int = 4) -> dict:
    """{city_id: [[provider, n], ...]} the providers reporting most places in each city."""
    rows = con.execute(f"""
        WITH t AS (
            SELECT city_id::VARCHAR AS city_id, provider, sum(n)::BIGINT AS n
            FROM read_csv_auto('{sources_csv}')
            GROUP BY 1, 2
        )
        SELECT city_id, provider, n FROM t
        QUALIFY row_number() OVER (PARTITION BY city_id ORDER BY n DESC) <= {top}
        ORDER BY city_id, n DESC
    """).fetchall()
    out: dict = {}
    for cid, prov, n in rows:
        out.setdefault(cid, []).append([prov, n])
    return out


def provider_order(con, sources_csv) -> list:
    """All providers, most places first (for the Sources line)."""
    return [r[0] for r in con.execute(f"""
        SELECT provider FROM read_csv_auto('{sources_csv}')
        GROUP BY 1 ORDER BY sum(n) DESC
    """).fetchall()]


def _keep_cities_sql(csv_path, max_points) -> str:
    """Whole cities, largest population first, until max_points (single-file mode only)."""
    if max_points is None:
        return ""
    return f"""
        JOIN (
            SELECT city_id FROM (
                SELECT city_id::VARCHAR AS city_id,
                       sum(n_coffee + n_bakery) OVER (ORDER BY pop DESC ROWS UNBOUNDED PRECEDING) AS cum
                FROM read_csv_auto('{csv_path}') WHERE n_coffee + n_bakery > 0
            ) WHERE cum <= {int(max_points)}
        ) k ON k.city_id = p.city_id::VARCHAR"""


def places(con, csv_path, points_path, max_points=None) -> tuple[list, list, dict]:
    """Coffee and bakery points as [lon, lat, group (0 coffee, 1 bakery), name, [provider codes]].
    Providers are stored once, as small integer codes, to keep files light."""
    rows = con.execute(f"""
        SELECT round(lon, 5), round(lat, 5), CASE grp WHEN 'coffee' THEN 0 ELSE 1 END, name, datasets
        FROM read_parquet('{points_path}') p
        {_keep_cities_sql(csv_path, max_points)}
        WHERE grp IN ('coffee', 'bakery') AND lon IS NOT NULL AND lat IS NOT NULL
    """).fetchall()
    total = con.execute(f"""
        SELECT count(*) FROM read_parquet('{points_path}') WHERE grp IN ('coffee', 'bakery')
    """).fetchone()[0]
    providers = sorted({d for r in rows for d in (r[4] or [])})
    code = {p: i for i, p in enumerate(providers)}
    pts = [[r[0], r[1], r[2], r[3], [code[d] for d in (r[4] or [])]] for r in rows]
    return pts, providers, {"points_total": total, "points_on_map": len(pts)}


def tile_key(lon: float, lat: float, deg: float) -> str:
    """Grid cell of a point, e.g. '-88_14' for 1-degree cells (lower-left corner / deg)."""
    return f"{math.floor(lon / deg)}_{math.floor(lat / deg)}"


def split_tiles(points: list, deg: float) -> dict:
    out: dict = {}
    for p in points:
        out.setdefault(tile_key(p[0], p[1], deg), []).append(p)
    return out
