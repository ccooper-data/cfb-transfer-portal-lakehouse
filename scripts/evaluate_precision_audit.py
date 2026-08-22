from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.precision_audit import evaluate_precision_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the locked resolver-v1 precision audit.")
    parser.add_argument("labels_csv", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    with args.labels_csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    result = evaluate_precision_audit(rows)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
