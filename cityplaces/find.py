"""Find every Overture place of one or more brands or names worldwide (e.g. "Equinox").

Matches, case-insensitively, places whose brand name or primary name starts with the
search text. Nothing is decided for you: every match is kept with its category label,
brand, country and providers, so you can see what else shares the name (an "Equinox"
hotel, salon or apartment block) and filter it yourself.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from . import __project__, __version__
from .config import overture_glob
from .provenance import git_commit, sha256


def _sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "search"


def build_find_sql(cfg: dict, names: list[str], out_path, labels: list[str] | None = None,
                   contains: bool = False, country: str | None = None) -> str:
    """names: one or more search texts. Prefix match by default ("cyber" finds "Cyber Gym");
    contains=True also finds it in the middle ("Gimnasio Cyber")."""
    o = cfg["overture"]
    field, brand_field = o["category_field"], o.get("brand_field", "brand.names.primary")
    lead = "%" if contains else ""
    pats = [(n, _sql_str(lead + n.lower().replace("%", "") + "%")) for n in names]
    def any_like(col):
        return "(" + " OR ".join(f"lower({col}) LIKE {pt}" for _, pt in pats) + ")"
    keep = f"({any_like(f'p.{brand_field}')} OR {any_like('p.names.primary')})"
    # which search text matched (first that fits, brand before name)
    which = "CASE " + " ".join(
        f"WHEN lower(p.{brand_field}) LIKE {pt} OR lower(p.names.primary) LIKE {pt} THEN {_sql_str(n)}"
        for n, pt in pats) + " END"
    brand_hit = any_like(f"p.{brand_field}")
    if labels:
        keep += f" AND p.{field} IN ({', '.join(_sql_str(x) for x in labels)})"
    if country:
        keep += f" AND p.addresses[1].country = {_sql_str(country.upper())}"
    excl = ", ".join(_sql_str(x) for x in o.get("exclude_providers", []))
    datasets = "list_sort(list_distinct(list_transform(p.sources, lambda s: s.dataset)))"
    if excl:
        datasets = f"list_filter({datasets}, lambda d: d NOT IN ({excl}))"
    return f"""
        COPY (
            SELECT p.id,
                   {which}                                AS search,
                   p.names.primary                        AS name,
                   p.{brand_field}                        AS brand,
                   p.{field}                              AS label,
                   p.addresses[1].country                 AS country,
                   p.addresses[1].locality                AS locality,
                   p.confidence,
                   array_to_string({datasets}, '; ')      AS providers,
                   CASE WHEN {brand_hit} THEN 'brand' ELSE 'name' END AS matched_by,
                   round((p.bbox.ymin + p.bbox.ymax) / 2, 6) AS lat,
                   round((p.bbox.xmin + p.bbox.xmax) / 2, 6) AS lon
            FROM read_parquet('{overture_glob(cfg)}', hive_partitioning=1) p
            WHERE {keep}
              AND p.confidence >= {float(o['min_confidence'])}
            ORDER BY search, country, locality, name
        ) TO '{out_path}' (HEADER, DELIMITER ',')
    """


def find_places(con, cfg: dict, names: list[str], labels: list[str] | None = None,
                contains: bool = False, country: str | None = None) -> dict:
    """Writes outputs/find/<slug>_<time>/places.csv, summary.txt and provenance.json."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(cfg["run"]["output_dir"]) / "find" / f"{slug('-'.join(names))[:60]}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv = out_dir / "places.csv"
    con.execute(build_find_sql(cfg, names, csv, labels, contains, country))

    q = duckdb.connect()
    total = q.execute(f"SELECT count(*) FROM read_csv_auto('{csv}')").fetchone()[0]
    by_label = q.execute(f"SELECT coalesce(label,'(none)') AS label, count(*) n FROM read_csv_auto('{csv}') "
                         "GROUP BY 1 ORDER BY n DESC").fetchall()
    by_country = q.execute(f"SELECT coalesce(country,'(none)') AS country, count(*) n FROM read_csv_auto('{csv}') "
                           "GROUP BY 1 ORDER BY n DESC").fetchall()
    by_match = dict(q.execute(f"SELECT matched_by, count(*) FROM read_csv_auto('{csv}') GROUP BY 1").fetchall())
    by_search = q.execute(f"SELECT search, count(*) n FROM read_csv_auto('{csv}') GROUP BY 1 ORDER BY n DESC").fetchall()

    how = "containing" if contains else "starting with"
    lines = [f"Search: names or brands {how} " + ", ".join(f"'{n}'" for n in names) + " (case-insensitive)",
             f"Country filter: {country.upper() if country else 'none (worldwide)'}",
             f"Overture release: {cfg['overture']['release']} · min confidence {cfg['overture']['min_confidence']}",
             f"Category filter: {', '.join(labels) if labels else 'none (all categories)'}",
             f"Matches: {total} (brand {by_match.get('brand', 0)}, name only {by_match.get('name', 0)})", "",
             "By search text:"] + [f"  {n:6d}  {t}" for t, n in by_search] + ["",
             "By category label (check which ones are really what you searched for):"]
    lines += [f"  {n:6d}  {lab}" for lab, n in by_label]
    lines += ["", "By country:"] + [f"  {n:6d}  {c}" for c, n in by_country]
    (out_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    prov = {"project": __project__, "pipeline": "city_places", "step": "find",
            "script_version": __version__, "git_commit": git_commit(),
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "search": names, "match": "contains" if contains else "prefix",
            "country_filter": country.upper() if country else None, "category_filter": labels or None,
            "overture_release": cfg["overture"]["release"], "source": overture_glob(cfg),
            "min_confidence": cfg["overture"]["min_confidence"],
            "config_sha256": sha256(cfg["_path"]), "matches": total,
            "output": csv.name, "output_sha256": sha256(csv),
            "license": "CDLA-Permissive-2.0 (check per-source attribution in Overture docs)"}
    (out_dir / "provenance.json").write_text(json.dumps(prov, indent=2))
    return {"dir": out_dir, "matches": total, "summary": "\n".join(lines)}
