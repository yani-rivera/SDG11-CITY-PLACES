"""Load GHSL Urban Centre polygons, reproject to WGS84."""


def _crs_label(crs) -> str:
    if isinstance(crs, dict):
        auth = crs.get("auth_name"), crs.get("auth_code")
        if all(auth):
            return f"{auth[0]}:{auth[1]}"
        return (crs.get("wkt") or crs.get("projjson") or "")[:40]
    return str(crs or "")


def inspect_cities(con, cfg: dict) -> tuple[str, bool]:
    """Readable summary of the GeoPackage: layers, counts, geometry, field names.
    Field names are checked only on the layer the config reads (`cities.layer`).
    Returns (text, ok)."""
    c = cfg["cities"]
    rel = con.execute(f"SELECT * FROM ST_Read_Meta('{c['path']}')")
    cols = [d[0] for d in rel.description]
    row = dict(zip(cols, rel.fetchone()))
    wanted = {k: c.get(k) for k in ("id_field", "name_field", "country_field", "pop_field")}
    layers = row.get("layers") or []
    target = c.get("layer") or (layers[0].get("name") if layers else None)

    lines = [f"file: {c['path']}", f"layers: {len(layers)}", f"config reads layer: {target}", ""]
    ok, found = True, False
    for lyr in layers:
        fields = [f.get("name") for f in (lyr.get("fields") or [])]
        geoms = [f"{g.get('name')} ({g.get('type')}, {_crs_label(g.get('crs'))})"
                 for g in (lyr.get("geometry_fields") or [])]
        used = lyr.get("name") == target
        found |= used
        lines.append(f"== layer: {lyr.get('name')}   features: {lyr.get('feature_count')}"
                     f"{'   <- used' if used else '   (not used)'}")
        lines.append(f"   geometry: {', '.join(geoms) or 'none'}")
        lines.append(f"   {len(fields)} fields:")
        lines += [f"     {', '.join(fields[i:i + 6])}" for i in range(0, len(fields), 6)]
        if used:
            lines.append("   config check:")
            for key, name in wanted.items():
                hit = name in fields
                ok &= hit
                lines.append(f"     {key:14s} {name!s:28s} {'OK' if hit else 'NOT FOUND'}")
        lines.append("")
    if not found:
        ok = False
        lines.append(f"Layer '{target}' is not in the file: set `cities.layer` to one of the layer names above.")
    return "\n".join(lines), ok


def load_cities(con, cfg: dict) -> int:
    c = cfg["cities"]
    layer = f", layer='{c['layer']}'" if c.get("layer") else ""
    con.execute(f"""
        CREATE OR REPLACE TABLE cities AS
        WITH raw AS (SELECT * FROM ST_Read('{c['path']}'{layer}))
        SELECT CAST("{c['id_field']}" AS VARCHAR)   AS city_id,
               "{c['name_field']}"                   AS city,
               "{c['country_field']}"                AS country,
               CAST("{c['pop_field']}" AS DOUBLE)    AS pop,
               ST_Transform(geom, '{c['source_crs']}', 'EPSG:4326', always_xy := true) AS geom
        FROM raw
    """)
    con.execute("""
        ALTER TABLE cities ADD COLUMN xmin DOUBLE; ALTER TABLE cities ADD COLUMN xmax DOUBLE;
        ALTER TABLE cities ADD COLUMN ymin DOUBLE; ALTER TABLE cities ADD COLUMN ymax DOUBLE;
        ALTER TABLE cities ADD COLUMN cx DOUBLE;   ALTER TABLE cities ADD COLUMN cy DOUBLE;
        UPDATE cities SET xmin=ST_XMin(geom), xmax=ST_XMax(geom),
                          ymin=ST_YMin(geom), ymax=ST_YMax(geom),
                          cx=ST_X(ST_PointOnSurface(geom)), cy=ST_Y(ST_PointOnSurface(geom));
    """)
    return con.execute("SELECT count(*) FROM cities").fetchone()[0]
