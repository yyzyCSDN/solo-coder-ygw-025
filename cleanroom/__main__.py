from __future__ import annotations

import argparse
import json

from .service import CleanroomService


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a cleanroom control ledger")
    parser.add_argument("--db", default="cleanroom.db")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    service = CleanroomService(args.db)
    try:
        result = service.commission_pressure("demo-cycle", {"or-a": 15, "buffer-a": 10, "corridor": 7}) if args.demo else service.health()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        service.close()


if __name__ == "__main__":
    main()
