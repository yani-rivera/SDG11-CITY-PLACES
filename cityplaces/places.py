"""Extract coffee/bakery places from Overture to a local Parquet (one global pass).

A place is kept when its category label is in `groups`, or (if not) when its brand
is listed under `brands`. The label wins when both apply. `matched_by` records which.

Speed: the filter is written with constant IN-lists (not joins) so DuckDB can apply it
while scanning the Parquet files and only read the heavier columns (names, sources)
for rows that pass. Joins would force it to read every column of every place first.
"""
from .config import overture_glob, label_to_group, brand_to_group


def _sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _case(expr: str, mapping: dict[str, str]) -> str:
    """CASE expr WHEN 'a' THEN 'coffee' ... END"""
    whens = " ".join(f"WHEN {_sql_str(k)} THEN {_sql_str(v)}" for k, v in mapping.items())
    return f"CASE {expr} {whens} END"


def build_extract_sql(cfg: dict, out_path) -> str:
    o = cfg["overture"]
    field = o["category_field"]
    brand_field = o.get("brand_field", "brand.names.primary")
    labels = label_to_group(cfg)
    brands = brand_to_group(cfg)

    label_in = ", ".join(_sql_str(x) for x in labels)
    label_grp = _case(f"p.{field}", labels)
    if brands:
        brand_in = ", ".join(_sql_str(x) for x in brands)
        brand_grp = _case(f"lower(p.{brand_field})", brands)
        keep = f"(p.{field} IN ({label_in}) OR lower(p.{brand_field}) IN ({brand_in}))"
        grp = f"coalesce({label_grp}, {brand_grp})"
    else:
        keep = f"p.{field} IN ({label_in})"
        grp = label_grp

    return f"""
        COPY (
            SELECT p.id,
                   p.names.primary                     AS name,
                   p.{field}                           AS label,
                   p.{brand_field}                     AS brand,
                   {grp}                               AS grp,
                   CASE WHEN p.{field} IN ({label_in}) THEN 'label' ELSE 'brand' END AS matched_by,
                   p.confidence,
                   -- which data providers reported this place (a place can have several)
                   list_sort(list_distinct(list_transform(p.sources, lambda s: s.dataset))) AS datasets,
                   (p.bbox.xmin + p.bbox.xmax) / 2     AS lon,
                   (p.bbox.ymin + p.bbox.ymax) / 2     AS lat
            FROM read_parquet('{overture_glob(cfg)}', hive_partitioning=1) p
            WHERE {keep}
              AND p.confidence >= {float(o['min_confidence'])}
        ) TO '{out_path}' (FORMAT parquet, COMPRESSION zstd)
    """


def extract_places(con, cfg: dict, out_path) -> dict:
    con.execute(build_extract_sql(cfg, out_path))
    counts = con.execute(f"""
        SELECT grp, matched_by, count(*) FROM read_parquet('{out_path}')
        GROUP BY ALL ORDER BY 1, 2
    """).fetchall()
    return {
        "rows_by_group": {f"{g} ({m})": n for g, m, n in counts},
        "labels": label_to_group(cfg),
        "brands": brand_to_group(cfg),
    }
