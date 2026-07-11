from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ecdb import ECDB

CHANGED_BY = "system:threshold-script"
SOURCE_SCRIPT = "set_mcb_category_threshold.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set an MCB approval threshold for a category atomically.")
    parser.add_argument("--category", required=True, help="Category key, such as headset or general_retail")
    parser.add_argument("--threshold", required=True, type=float, help="Approval confidence threshold between 0 and 1")
    parser.add_argument("--reason", default=None, help="Optional human-readable reason for the change")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = ECDB(prefer_rest=False)
    row = db.set_mcb_category_threshold(
        category=args.category,
        approval_confidence_threshold=args.threshold,
        changed_by=CHANGED_BY,
        change_reason=args.reason,
        source_script=SOURCE_SCRIPT,
    )
    print(f"Updated threshold for {row.get('category')} to {row.get('approval_confidence_threshold')}")
    print(f"Changed by: {row.get('changed_by')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
