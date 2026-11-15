"""Load and validate the YAML config."""
from pathlib import Path
import yaml

REQUIRED = {
    "overture": ["release", "s3_path", "s3_region", "category_field", "min_confidence"],
    "cities": ["path", "source_crs", "id_field", "name_field", "country_field", "pop_field"],
}


def load_config(path: str | Path) -> dict:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for section, keys in REQUIRED.items():
        missing = [k for k in keys if k not in cfg.get(section, {})]
        if missing:
            raise ValueError(f"config [{section}] missing: {missing}")
    if not cfg.get("groups"):
        raise ValueError("config needs at least one entry under `groups`")
    cfg["_path"] = str(path.resolve())
    return cfg


def overture_glob(cfg: dict) -> str:
    o = cfg["overture"]
    return o["s3_path"].format(release=o["release"])


def brand_to_group(cfg: dict) -> dict[str, str]:
    """Flatten optional `brands` into {lowercased brand: group}."""
    out: dict[str, str] = {}
    for group, names in (cfg.get("brands") or {}).items():
        if group not in cfg["groups"]:
            raise ValueError(f"brands: group '{group}' is not one of {list(cfg['groups'])}")
        for name in names:
            key = name.strip().lower()
            if key in out:
                raise ValueError(f"brand '{name}' is in both '{out[key]}' and '{group}'")
            out[key] = group
    return out


def label_to_group(cfg: dict) -> dict[str, str]:
    """Flatten groups into {label: group}; a label may belong to one group only."""
    out: dict[str, str] = {}
    for group, labels in cfg["groups"].items():
        for lab in labels:
            if lab in out:
                raise ValueError(f"label '{lab}' is in both '{out[lab]}' and '{group}'")
            out[lab] = group
    return out
