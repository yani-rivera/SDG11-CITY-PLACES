# Security

The map page shows text that comes from outside: place names in Overture Maps are written by
businesses and the public, and anyone can create one. The page treats every such text as data.

## How the map page is protected

- **Names are never run as code.** Data sits in `<script type="application/json">` blocks or in
  `.json` files and is read with `JSON.parse`. `<` is escaped in embedded JSON, so a name cannot
  close the block. Names reach the page only through `textContent`, never `innerHTML`.
- **Content-Security-Policy** (in `index.html`): scripts may come only from the pinned MapLibre file
  and the page's own inline script, identified by its SHA-256 hash; network requests may go only to
  the page's own site and the basemap server. No forms, no `<base>` changes, no plug-ins.
- **Pinned library with Subresource Integrity:** MapLibre GL JS 4.7.1 from unpkg, with `sha384`
  hashes for the script and the stylesheet (`cityplaces/mapsafe.py`). If the CDN file ever changes,
  the browser refuses it and the page says the library did not load.
- **Checked links:** links in the Sources list are written only if they are plain `http(s)` URLs;
  the basemap and its servers must be `https`. Colours must be hex codes.
- **No keys or secrets:** the basemap (OpenFreeMap) needs no API key, so nothing secret is
  published with the page.
- **`serve` listens on 127.0.0.1 only**, so the preview is not reachable from other computers.
- The page stores one thing in the browser: whether the legend is folded.

## Upgrading MapLibre

Change the version in `cityplaces/mapsafe.py` and recompute both hashes:

```
curl -sL https://unpkg.com/maplibre-gl@<version>/dist/maplibre-gl.js  | openssl dgst -sha384 -binary | base64
curl -sL https://unpkg.com/maplibre-gl@<version>/dist/maplibre-gl.css | openssl dgst -sha384 -binary | base64
```

## Changing the basemap

If a new style loads tiles, fonts or sprites from more than one server, list every server in
`map.basemap_origins`; otherwise the policy blocks them and the basemap stays blank.

## Reporting a problem

Open an issue on the repository, or write to the author through ORCID 0000-0003-3309-5256.
