#!/usr/bin/env python3
"""Platform-independent KoroFlow CLI. Mutations write local records only."""
import argparse
import json
import os
from pathlib import Path
import sys

from koroflow_core.core import Workspace, init, read


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=os.environ.get("KOROFLOW_WORKSPACE"), help="Existing video workspace root")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("init")
    create = subs.add_parser("create"); create.add_argument("--manifest", required=True)
    legacy = subs.add_parser("import-legacy"); legacy.add_argument("--inventory", required=True)
    legacy.add_argument("--work", required=True); legacy.add_argument("--project", required=True)
    status = subs.add_parser("status"); status.add_argument("--work", required=True)
    route = subs.add_parser("route"); route.add_argument("--operation", required=True)
    route.add_argument("--adapter"); route.add_argument("--requires", nargs="*", default=[])
    subs.add_parser("adapters")
    register = subs.add_parser("register"); register.add_argument("--work", required=True)
    register.add_argument("--revision", required=True); register.add_argument("--file", required=True)
    register.add_argument("--provenance", required=True)
    review = subs.add_parser("review"); review.add_argument("--work", required=True)
    review.add_argument("--revision", required=True); review.add_argument("--report", required=True)
    deliver = subs.add_parser("deliver"); deliver.add_argument("--work", required=True)
    deliver.add_argument("--revision", required=True); deliver.add_argument("--title-en", required=True)
    deliver.add_argument("--hashtags", nargs="*", default=[]); deliver.add_argument("--evidence", required=True)
    state = subs.add_parser("state"); state.add_argument("--work", required=True)
    state.add_argument("--action", choices=["paused", "cancelled", "resumed", "adopted"], required=True)
    state.add_argument("--evidence", required=True)
    prepare = subs.add_parser("prepare"); prepare.add_argument("--work", required=True)
    prepare.add_argument("--task", required=True); prepare.add_argument("--adapter", required=True)
    prepare.add_argument("--operation", required=True); prepare.add_argument("--request", required=True)
    prepare.add_argument("--requires", nargs="*", default=[]); prepare.add_argument("--account")
    update = subs.add_parser("record-task"); update.add_argument("--work", required=True)
    update.add_argument("--task", required=True); update.add_argument("--status", required=True)
    update.add_argument("--evidence", required=True); update.add_argument("--remote-id")
    update.add_argument("--output"); update.add_argument("--cost", help='JSON with amount and explicit unit')
    report = subs.add_parser("report"); report.add_argument("--date", required=True)
    bridge = subs.add_parser("bridge"); bridge.add_argument("--work", required=True)
    args = parser.parse_args(argv)
    try:
        if not args.workspace:
            raise ValueError("Select --workspace or KOROFLOW_WORKSPACE; no production directory is assumed")
        if args.command == "init":
            result = init(args.workspace)
        else:
            ws = Workspace(args.workspace)
            if args.command == "create":
                manifest = read(args.manifest)
                if not Path(manifest["project"]).is_absolute():
                    manifest["project"] = str(Path(args.manifest).resolve().parent / manifest["project"])
                result = ws.create(manifest)
            elif args.command == "import-legacy": result = ws.import_legacy(args.inventory, args.work, args.project)
            elif args.command == "status": result = ws.work(args.work)
            elif args.command == "route": result = ws.route(args.operation, args.requires, args.adapter)
            elif args.command == "adapters": result = {"adapters": ws.setting("adapters"), "external_execution": False}
            elif args.command == "register": result = ws.register(args.work, args.revision, args.file, args.provenance)
            elif args.command == "review": result = ws.review(args.work, args.revision, read(args.report))
            elif args.command == "deliver": result = ws.deliver(args.work, args.revision, args.title_en, args.hashtags, args.evidence)
            elif args.command == "state": result = ws.state(args.work, args.action, args.evidence)
            elif args.command == "prepare": result = ws.prepare(args.work, args.task, args.adapter, args.operation, args.request, args.requires, args.account)
            elif args.command == "record-task": result = ws.task_update(args.work, args.task, args.status, args.evidence, args.remote_id, args.output, json.loads(args.cost) if args.cost else None)
            elif args.command == "report": result = ws.report(args.date)
            else: result = ws.bridge(args.work)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"error": str(exc), "external_execution": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
