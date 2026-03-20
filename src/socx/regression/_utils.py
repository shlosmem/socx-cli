from __future__ import annotations

import re

from pydantic import UUID4


def _safe_dir_name(name: str, node_id: UUID4) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-").lower()
    return f"{slug or 'item'}-{node_id}"
