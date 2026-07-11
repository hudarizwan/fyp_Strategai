from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ecdb import ECDB


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Set the active analytics model version atomically in PostgreSQL.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', dest='version_id', help='Model version UUID')
    group.add_argument('--version-tag', dest='version_tag', help='Model version tag')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = ECDB(prefer_rest=False)

    if args.version_id:
        version = db.get_analytics_model_version_by_id(args.version_id)
    else:
        version = db.get_analytics_model_version_by_tag(args.version_tag)

    if not version:
        print('Model version not found.', file=sys.stderr)
        return 1

    active = db.set_active_analytics_model_version(str(version['id']))
    print(f"Activated model version {active.get('version_tag')} ({active.get('id')})")
    print(f"Artifact path: {active.get('artifact_path')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
