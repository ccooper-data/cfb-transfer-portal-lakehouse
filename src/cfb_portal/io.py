from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, object]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
