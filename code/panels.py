"""Shared helpers: find a figure's panel images and split its caption into per-panel parts."""
import re
from pathlib import Path
from PIL import Image


def panels(fig_dir: Path, key: str):
    return sorted(fig_dir.glob(f"{key}_[a-z].png"))


def split_caption(cap: str):
    """'Lead. (a) one. (b) two.' -> ('Lead.', {'a': 'one.', 'b': 'two.'})."""
    parts = re.split(r"\(([a-e])\)\s*", cap)
    lead, out = parts[0].strip(), {}
    for i in range(1, len(parts) - 1, 2):
        out[parts[i]] = parts[i + 1].strip()
    return lead, out


def width_in(path: Path, max_w=6.3, max_h=8.2):
    w, h = Image.open(path).size
    return round(min(max_w, max_h * w / h), 2)
