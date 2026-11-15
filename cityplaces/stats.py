"""Summary numbers for the dataset README and Zenodo description (the [[PLACEHOLDERS]])."""
import json
from pathlib import Path


def run_stats(con, run_dir: Path, focus_city: str = "Tegucigalpa") -> dict:
    counts = run_dir / "city_counts.csv"
    points = run_dir / "points_in_cities.parquet"
    sources = run_dir / "city_sources.csv"
    prov = json.loads((run_dir / "provenance.json").read_text())

    n_coffee, n_bakery, n_cities_with = con.execute(f"""
        SELECT sum(n_coffee), sum(n_bakery), count(*) FILTER (WHERE n_coffee + n_bakery > 0)
        FROM read_csv_auto('{counts}')
    """).fetchone()
    providers = [r[0] for r in con.execute(f"""
        SELECT provider FROM read_csv_auto('{sources}') GROUP BY 1 ORDER BY sum(n) DESC
    """).fetchall()]
    # share of the focus city's places whose ONLY provider is meta
    total, meta_only = con.execute(f"""
        SELECT count(*), count(*) FILTER (WHERE datasets = ['meta'])
        FROM read_parquet('{points}') p
        JOIN read_csv_auto('{counts}') c ON c.city_id::VARCHAR = p.city_id::VARCHAR
        WHERE c.city = ?
    """, [focus_city]).fetchone()
    steps = prov.get("steps", [])
    versions = sorted({s.get("script_version") for s in steps if s.get("script_version")})
    rid = prov["run_id"]
    return {
        "RUN_ID": rid,
        "ACCESS_DATE": f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}",
        "VERSION": ", ".join(versions) or prov.get("script_version"),
        "N_IN_CITIES": f"{int(n_coffee + n_bakery):,}",
        "N_COFFEE": f"{int(n_coffee):,}",
        "N_BAKERY": f"{int(n_bakery):,}",
        "N_CITIES_WITH_PLACES": f"{int(n_cities_with):,}",
        "PROVIDERS": ", ".join(providers),
        "TEGUS_META_SHARE": (f"{meta_only} of {total} ({100 * meta_only / total:.0f}%)"
                             if total else f"no places found for {focus_city}"),
    }
