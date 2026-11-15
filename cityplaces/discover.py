"""List candidate category labels (with global counts) so you choose the groups, not me."""
from .config import overture_glob


def discover_labels(con, cfg: dict):
    field = cfg["overture"]["category_field"]
    pats = cfg["discover"]["patterns"]
    cond = " OR ".join(f"lower({field}) LIKE ?" for _ in pats)
    sql = f"""
        SELECT {field} AS label, basic_category, count(*) AS n
        FROM read_parquet('{overture_glob(cfg)}', hive_partitioning=1)
        WHERE {cond}
        GROUP BY ALL
        ORDER BY n DESC
    """
    return con.execute(sql, [p.lower() for p in pats]).df()
