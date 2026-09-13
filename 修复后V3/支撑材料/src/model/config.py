from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path) -> dict[str, Any]:
    """Load final.yaml.

    The file intentionally uses JSON syntax, which is a strict subset of YAML.  This
    keeps the pipeline dependency-free while remaining readable by YAML tooling.
    """
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["_config_path"] = str(p.resolve())
    source_value=os.environ.get("CUMCM_SOURCE_ROOT",cfg["source_root"])
    source=Path(source_value)
    if not source.is_absolute(): source=PROJECT_ROOT/source
    cfg["_source_root"]=str(source.resolve())
    out = Path(cfg["output_root"])
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    cfg["_output_root"] = str(out.resolve())
    return cfg
