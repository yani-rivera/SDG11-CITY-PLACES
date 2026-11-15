"""DuckDB connection with the spatial and httpfs extensions."""
import duckdb


def connect(s3_region: str | None = None, threads: int | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for ext in ("spatial", "httpfs"):
        con.install_extension(ext)
        con.load_extension(ext)
    if s3_region:
        con.execute(f"SET s3_region='{s3_region}'")  # Overture bucket is public: no keys
    if threads:
        con.execute(f"SET threads={int(threads)}")
    # show DuckDB's progress bar for long queries (the global Overture scans)
    con.execute("SET enable_progress_bar=true")
    con.execute("SET enable_progress_bar_print=true")
    return con
