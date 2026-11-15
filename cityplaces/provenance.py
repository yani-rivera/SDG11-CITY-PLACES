"""Provenance: run id, script version, config copy, input hashes, step log."""
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from . import __version__, __project__


def sha256(path: str | Path, chunk: int = 1 << 20) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return None


class Run:
    """One pipeline run = one folder outputs/<run_id>/ with a provenance.json."""

    def __init__(self, cfg: dict, run_dir: str | Path | None = None):
        self.cfg = cfg
        if run_dir:
            self.dir = Path(run_dir)
            self.prov = json.loads((self.dir / "provenance.json").read_text())
        else:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            self.dir = Path(cfg["run"]["output_dir"]) / run_id
            self.dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(cfg["_path"], self.dir / "config.yaml")
            self.prov = {
                "run_id": run_id,
                "project": __project__,
                "pipeline": "city_places",
                "script_version": __version__,
                "git_commit": git_commit(),
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "config_sha256": sha256(cfg["_path"]),
                "environment": {
                    "python": sys.version.split()[0],
                    "duckdb": duckdb.__version__,
                    "platform": platform.platform(),
                },
                "sources": {
                    "overture_places": {
                        "release": cfg["overture"]["release"],
                        "license": "CDLA-Permissive-2.0 (check per-source attribution in Overture docs)",
                    },
                    "ghsl_ucdb": {
                        "path": cfg["cities"]["path"],
                        "version": cfg["cities"].get("version"),
                        "citation": cfg["cities"].get("citation"),
                        "sha256": sha256(cfg["cities"]["path"]),
                    },
                },
                "steps": [],
            }
            self.save()

    def log_step(self, name: str, **info):
        """Record a finished step with the code version and config that actually ran it
        (a run folder can be revisited later with newer code, e.g. `count --run`)."""
        self.prov["steps"].append({
            "step": name,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "script_version": __version__,
            "git_commit": git_commit(),
            "config_sha256": sha256(self.cfg["_path"]),
            **info,
        })
        self.save()

    def save(self):
        (self.dir / "provenance.json").write_text(json.dumps(self.prov, indent=2))
