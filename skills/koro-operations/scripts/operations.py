#!/usr/bin/env python3
"""Portable, offline checks for production records and publication plans (stdlib only)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FORMAT = "koro.operations@1"
RELEASED_PUBLICATIONS = {"failed", "skipped", "cancelled"}


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def zone(name):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Timezone unavailable: {name}; install Python tzdata on this machine.") from exc


def timestamp(value, require_offset=False):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO 8601 string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if require_offset and result.tzinfo is None:
        raise ValueError("Timestamp needs an explicit timezone offset")
    return result


def issue(issues, code, detail, source=None, severity="error"):
    item = {"severity": severity, "code": code, "detail": detail}
    if source is not None:
        item["source"] = str(source)
    issues.append(item)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Context:
    def __init__(self, config_file):
        self.file = Path(config_file).resolve()
        self.data = read_json(self.file)
        if not isinstance(self.data, dict) or self.data.get("format") != FORMAT:
            raise ValueError(f"Expected configuration format {FORMAT}")
        self.timezone = self.data.get("timezone", "Asia/Shanghai")
        self.zone = zone(self.timezone)
        self.paths = self.data.get("paths", {})
        if not isinstance(self.paths, dict) or not self.paths.get("projects"):
            raise ValueError("Configuration needs paths.projects")

    def path(self, name):
        value = self.paths.get(name)
        if not value:
            return None
        path = Path(value).expanduser()
        return path.resolve() if path.is_absolute() else (self.file.parent / path).resolve()


def account_key(account):
    if account.get("account_id"):
        return account["account_id"]
    if account.get("device_ip") and account.get("container_id"):
        return f"cloud:{account['device_ip']}:{account['container_id']}"
    if account.get("tiktok_username"):
        return "tiktok:" + account["tiktok_username"].lstrip("@").casefold()
    raise ValueError("Account needs account_id, device_ip + container_id, or tiktok_username")


def accounts(ctx, issues):
    file = ctx.path("publishing_accounts")
    if not file or not file.is_file():
        issue(issues, "missing_accounts", "Configure a local publishing account registry", file)
        return []
    raw = read_json(file)
    rows = raw.get("accounts", []) if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("Publishing registry must contain an accounts list")
    result = []
    seen = set()
    for row in rows:
        try:
            key = account_key(row)
        except (ValueError, TypeError, AttributeError) as exc:
            issue(issues, "invalid_account", str(exc), file)
            continue
        if key in seen:
            issue(issues, "duplicate_account", key, file)
            continue
        seen.add(key)
        result.append({**row, "account_id": key})
    snapshot = ctx.path("account_snapshot")
    if snapshot and snapshot.is_file():
        state = read_json(snapshot)
        observations = {account_key(a): a for a in state.get("usable_accounts", [])}
        for row in result:
            observed = observations.get(row["account_id"])
            if observed:
                row["login_observation"] = {"status": "logged_in", "checked_at": observed.get("checked_at", state.get("checked_at"))}
                for field in ("tiktok_username", "tiktok_nickname"):
                    if observed.get(field):
                        row[field] = observed[field]
        for excluded in state.get("excluded_accounts", []):
            matches = [a for a in result if a.get("window") == excluded.get("window")
                       and (not excluded.get("device_ip") or a.get("device_ip") == excluded["device_ip"])]
            if len(matches) == 1:
                matches[0]["login_observation"] = {"status": "unavailable", "checked_at": state.get("checked_at"),
                                                   "detail": excluded.get("status")}
    return result


def metadata_files(root):
    """Do not traverse junctions/symlinks used as role shortcuts."""
    seen = set()
    for directory, children, filenames in os.walk(root, followlinks=False):
        path = Path(directory)
        resolved = path.resolve()
        if resolved in seen:
            children[:] = []
            continue
        seen.add(resolved)
        children[:] = sorted(name for name in children if name not in {".git", ".hypit", "node_modules"}
                             and not (path / name).is_symlink()
                             and not (hasattr(os.path, "isjunction") and os.path.isjunction(path / name)))
        if path.name == "项目文件" and "发布信息.json" in filenames:
            yield path / "发布信息.json"


def inventory(ctx, hash_files=False):
    issues, works = [], {}
    root = ctx.path("projects")
    if not root.is_dir():
        issue(issues, "missing_projects", "Project root is not a directory", root)
        return {"works": [], "issues": issues}
    for file in metadata_files(root):
        try:
            meta = read_json(file)
            if not isinstance(meta, dict):
                raise ValueError("Metadata must be an object")
            for field in ("work_id", "role", "content", "title_en", "updated_at"):
                if not isinstance(meta.get(field), str) or not meta[field].strip():
                    raise ValueError(f"Missing text field: {field}")
            if not isinstance(meta.get("hashtags"), list) or not all(isinstance(t, str) for t in meta["hashtags"]):
                raise ValueError("hashtags must be a list of strings")
            stamp = timestamp(meta["updated_at"], require_offset=True)
        except (ValueError, OSError, TypeError) as exc:
            issue(issues, "invalid_metadata", str(exc), file)
            continue
        work_id = meta["work_id"]
        first_issue = len(issues)
        project = file.parent.parent
        work = works.setdefault(work_id, {"work_id": work_id, "role": meta["role"], "projects": [], "_versions": [], "_events": []})
        if work["role"] != meta["role"]:
            issue(issues, "role_conflict", f"{work_id}: {work['role']} / {meta['role']}", file)
        work["projects"].append(str(project))
        work["_versions"].append((stamp, str(file), meta))
        event_dir = file.parent / "统计事件"
        for event_file in sorted(event_dir.glob("*.json")):
            try:
                event = read_json(event_file)
                if event.get("work_id") != work_id:
                    issue(issues, "event_work_mismatch", f"Expected {work_id}", event_file)
                    continue
                if event.get("role") and event["role"] != meta["role"]:
                    raise ValueError("Event role differs from work metadata")
                event_type = event.get("event")
                if event_type not in {"in_progress", "delivered", "adopted", "paused", "cancelled", "withdrawn"}:
                    raise ValueError(f"Unknown event: {event_type}")
                occurred = timestamp(event.get("occurred_at"))
                if occurred.tzinfo is None:
                    issue(issues, "naive_event_time", f"Interpreted in {ctx.timezone}", event_file, "warning")
                    occurred = occurred.replace(tzinfo=ctx.zone)
                if event_type in {"delivered", "adopted"} and not event.get("evidence"):
                    raise ValueError("Delivery/adoption event needs evidence")
                if event_type in {"delivered", "adopted"} and event.get("delivered_on"):
                    datetime.strptime(event["delivered_on"], "%Y-%m-%d")
                work["_events"].append((occurred, str(event_file), event, project))
            except (ValueError, OSError, TypeError, AttributeError) as exc:
                issue(issues, "invalid_event", str(exc), event_file)
        if not event_dir.is_dir():
            issue(issues, "missing_events", f"{work_id}: no delivery inferred from media", file, "warning")
        for item in issues[first_issue:]:
            item["work_id"] = work_id
    rows = []
    for work_id, work in sorted(works.items()):
        first_issue = len(issues)
        versions = sorted(work.pop("_versions"), key=lambda x: (x[0], x[1]))
        events = sorted(work.pop("_events"), key=lambda x: (x[0], x[1]))
        meta = versions[-1][2]
        work.update({key: meta[key] for key in ("content", "title_en", "hashtags", "updated_at")})
        work.update(delivered=False, adopted=False, withdrawn=False, in_progress=False, revising=False,
                    selected_file=None, delivered_on=None)
        selection = None
        delivery_days = []
        for when, event_file, event, project in events:
            kind = event["event"]
            if kind in {"delivered", "adopted"}:
                work["delivered"] = True
                work["withdrawn"] = False
                work["in_progress"] = work["revising"] = False
                if kind == "adopted":
                    work["adopted"] = True
                # Adoption date is never silently substituted for a missing first delivery date.
                if event.get("delivered_on"):
                    delivery_days.append(event["delivered_on"])
                if event.get("file"):
                    selected = Path(event["file"])
                    selection = selected if selected.is_absolute() else project / selected
                    work["selection_evidence"] = event_file
            elif kind == "withdrawn":
                work["withdrawn"] = True
                work["in_progress"] = work["revising"] = False
            elif kind == "in_progress":
                work["revising" if work["delivered"] else "in_progress"] = True
            elif kind in {"paused", "cancelled"}:
                work["in_progress"] = work["revising"] = False
        work["delivered_on"] = min(delivery_days) if delivery_days else None
        if work["delivered"] and not work["delivered_on"]:
            issue(issues, "unknown_delivery_date", work_id, severity="warning")
        if selection is not None:
            work["selected_file"] = str(selection.resolve())
            if not selection.is_file():
                issue(issues, "missing_delivery_file", work_id, selection)
            elif hash_files:
                work["sha256"] = digest(selection)
        elif work["delivered"]:
            issue(issues, "missing_delivery_selection", work_id)
        for item in issues[first_issue:]:
            item["work_id"] = work_id
        rows.append(work)
    return {"works": rows, "issues": issues,
            "summary": {"works": len(rows), "delivered": sum(w["delivered"] and not w["withdrawn"] for w in rows),
                        "adopted": sum(w["adopted"] and not w["withdrawn"] for w in rows),
                        "in_progress": sum(w["in_progress"] and not w["withdrawn"] for w in rows),
                        "revising": sum(w["revising"] and not w["withdrawn"] for w in rows),
                        "available_deliveries": sum(w["delivered"] and not w["withdrawn"] and bool(w["selected_file"]) and Path(w["selected_file"]).is_file() for w in rows)},
            "coverage": "Projects with 项目文件/发布信息.json; historical files without metadata remain in the existing ledger. Generation counts come from the statistics snapshot."}


def history(ctx, registry, issues):
    directory = ctx.path("publication_tasks")
    if not directory or not directory.is_dir():
        issue(issues, "missing_publication_history", "A complete task directory is required for duplicate checking", directory)
        return []
    records = []
    for file in sorted(directory.glob("*.json")):
        try:
            task = read_json(file)
            if not isinstance(task, dict):
                raise ValueError("Task must be an object")
            items = task.get("items", task.get("videos", []))
            if not isinstance(items, list):
                raise ValueError("Task items/videos must be a list")
            for item in items:
                work_id = item.get("work_id") or item.get("record_id", "").removeprefix("work:")
                if not work_id:
                    continue
                account_id = item.get("account_id", task.get("account_id"))
                username = item.get("tiktok_username") or item.get("username") or task.get("tiktok_username")
                window = item.get("window", task.get("window"))
                ip = item.get("device_ip", task.get("device_ip"))
                matches = [a for a in registry if
                           (account_id and a["account_id"] == account_id) or
                           (not account_id and username and (a.get("tiktok_username") or "").lstrip("@").casefold() == username.lstrip("@").casefold()) or
                           (not account_id and not username and window and a.get("window") == window and (not ip or a.get("device_ip") == ip))]
                status = item.get("status", task.get("status", "unknown"))
                if not matches and status not in RELEASED_PUBLICATIONS:
                    records.append({"work_id": work_id, "account_id": None, "status": status,
                                    "sha256": item.get("sha256"), "source": str(file)})
                for account in matches:
                    records.append({"work_id": work_id, "account_id": account["account_id"], "status": status,
                                    "sha256": item.get("sha256"), "source": str(file)})
        except (ValueError, OSError, TypeError, AttributeError) as exc:
            issue(issues, "invalid_publication_history", str(exc), file)
    return records


def plan(ctx, request_file):
    request = read_json(request_file)
    if not isinstance(request, dict) or not isinstance(request.get("items"), list) or not request["items"]:
        raise ValueError("Plan request needs a non-empty items list")
    requested = {item.get("work_id") for item in request["items"] if isinstance(item, dict) and isinstance(item.get("work_id"), str)}
    inv = inventory(ctx)
    issues = [{**i, "severity": "warning", "outside_request": True}
              if i.get("work_id") not in requested else dict(i) for i in inv["issues"]]
    registry = accounts(ctx, issues)
    previous = history(ctx, registry, issues)
    by_work = {w["work_id"]: w for w in inv["works"]}
    by_account = {a["account_id"]: a for a in registry}
    seen_pairs, seen_hashes, cache, result = set(), set(), {}, []
    for number, item in enumerate(request["items"], 1):
        if not isinstance(item, dict):
            issue(issues, "invalid_plan_item", f"Item {number} must be an object")
            continue
        work_id, account_id = item.get("work_id"), item.get("account_id")
        work, account = by_work.get(work_id), by_account.get(account_id)
        if not work or not account:
            issue(issues, "unknown_plan_identity", f"Item {number}: use an existing work_id and stable account_id")
            continue
        pair = work_id, account_id
        if pair in seen_pairs:
            issue(issues, "duplicate_request", f"{work_id} / {account_id}")
        seen_pairs.add(pair)
        if not work["delivered"] or work["withdrawn"] or not work["selected_file"]:
            issue(issues, "unavailable_work", work_id)
            continue
        if account.get("enabled") is False or account.get("status") in {"logged_out", "disabled", "banned"}:
            issue(issues, "unavailable_account", account_id)
        if account.get("login_observation", {}).get("status") == "unavailable":
            issue(issues, "unavailable_account", f"{account_id}: last local observation unavailable")
        allowed = account.get("allowed_roles", [account.get("role")])
        if work["role"] not in allowed:
            issue(issues, "role_mismatch", f"{work_id}: {work['role']} not in configured account roles")
        path = Path(work["selected_file"])
        if not path.is_file():
            continue  # inventory already records the missing selection
        if str(path) not in cache:
            cache[str(path)] = digest(path)
        sha = cache[str(path)]
        if item.get("sha256") and item["sha256"] != sha:
            issue(issues, "version_mismatch", work_id)
        if (sha, account_id) in seen_hashes:
            issue(issues, "duplicate_file_in_request", f"{work_id} / {account_id}")
        seen_hashes.add((sha, account_id))
        for record in previous:
            same_work = record["work_id"] == work_id or record["sha256"] == sha
            if record["account_id"] is None and same_work:
                issue(issues, "unresolved_history_account", f"{work_id}: match the existing historical account before retry", record["source"])
            elif record["account_id"] == account_id and same_work:
                if record["status"] not in RELEASED_PUBLICATIONS:
                    issue(issues, "already_assigned_or_published", f"{work_id}: {record['status']}; verify before retry", record["source"])
        scheduled = item.get("scheduled_at")
        account_zone = account.get("timezone", ctx.timezone)
        try:
            selected_zone = zone(account_zone)
            if scheduled is not None:
                scheduled_time = timestamp(scheduled, require_offset=True)
                if scheduled_time <= datetime.now(timezone.utc):
                    raise ValueError("Scheduled time must be in the future")
                scheduled = scheduled_time.astimezone(selected_zone).isoformat()
        except (ValueError, TypeError) as exc:
            issue(issues, "invalid_schedule", f"{work_id}: {exc}")
        title = item.get("title_en", work["title_en"])
        tags = item.get("hashtags", work["hashtags"])
        if not isinstance(title, str) or not title.strip():
            issue(issues, "invalid_title", work_id)
        if not isinstance(tags, list) or not all(isinstance(t, str) and t.startswith("#") for t in tags):
            issue(issues, "invalid_hashtags", work_id)
        observation = account.get("login_observation")
        issue(issues, "live_account_check_required", f"{account_id}: local observations do not establish current publish permission", severity="warning")
        result.append({"work_id": work_id, "account_id": account_id, "window": account.get("window"),
                       "username": account.get("tiktok_username"), "source_file": str(path), "sha256": sha,
                       "title_en": title, "hashtags": tags, "cover": item.get("cover"),
                       "timezone": account_zone, "scheduled_at": scheduled, "mode": "scheduled" if scheduled else "immediate",
                       "last_login_observation": observation, "status": "proposed"})
    return {"format": "koro.publication-plan@1", "preflight_ok": not any(i["severity"] == "error" for i in issues),
            "executed": False, "reserved": False, "items": result, "issues": issues,
            "note": "Offline preflight only. No account login, reservation, upload, scheduling or ledger mutation occurred."}


def snapshot(ctx, day=None):
    file = ctx.path("statistics_snapshot")
    if not file or not file.is_file():
        raise ValueError("Configure an existing statistics_snapshot; no statistics will be invented")
    data = read_json(file)
    if day:
        datetime.strptime(day, "%Y-%m-%d")
    return {"source": str(file), "updated_at": data.get("updated_at"), "refreshed": False,
            "summary": data.get("summary"),
            "production_targets": [r for r in data.get("production_targets", []) if not day or r.get("date") == day],
            "note": "Existing snapshot, possibly stale. Generation, delivery and adoption retain their separate source definitions. Publishing accounts do not change production targets."}


def doctor(ctx):
    issues = []
    for name in ("projects", "production_targets", "statistics_snapshot", "publication_tasks", "publishing_accounts"):
        path = ctx.path(name)
        if not path or not path.exists():
            issue(issues, "missing_path", name, path, "error" if name == "projects" else "warning")
    rows = accounts(ctx, issues) if ctx.path("publishing_accounts") else []
    return {"format": FORMAT, "config": str(ctx.file), "timezone": ctx.timezone,
            "publishing_accounts": len(rows), "issues": issues, "network_checked": False,
            "note": "Local configuration only; no production refresh or platform session check."}


def init_config(destination, workspace):
    target = Path(destination).resolve()
    root = Path(workspace).resolve()
    config = {"format": FORMAT, "timezone": "Asia/Shanghai", "paths": {
        "projects": str(root / "视频项目"),
        "production_targets": str(root / "产量统计/账号配置.json"),
        "statistics_snapshot": str(root / "产量统计/outputs/20261015_video_stats/data.json"),
        "publication_tasks": str(root / "发布管理/发布任务"),
        "publishing_accounts": str(root / "发布管理/云手机账号映射.json"),
        "account_snapshot": None, "production_rules": str(root / "制片工作约定.md"),
        "creative_preferences": None}, "display": {"scheduled_counts_as_published": True}}
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"created": str(target), "format": FORMAT, "note": "Path configuration only; no projects, accounts or statistics modified."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a path-only local config; refuses overwrite")
    init.add_argument("--config", required=True)
    init.add_argument("--workspace", required=True)
    for command in ("doctor", "check", "accounts", "snapshot", "plan"):
        child = commands.add_parser(command)
        child.add_argument("--config", default=os.environ.get("KORO_OPERATIONS_CONFIG"))
        if command == "check":
            child.add_argument("--hash", action="store_true", help="Hash explicitly selected delivery files")
        if command == "snapshot":
            child.add_argument("--date")
        if command == "plan":
            child.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_config(args.config, args.workspace)
        else:
            if not args.config:
                raise ValueError("Use --config or KORO_OPERATIONS_CONFIG to select local configuration")
            ctx = Context(args.config)
            if args.command == "doctor":
                result = doctor(ctx)
            elif args.command == "check":
                result = inventory(ctx, args.hash)
            elif args.command == "accounts":
                issues = []
                result = {"accounts": accounts(ctx, issues), "issues": issues, "live_verified": False}
            elif args.command == "snapshot":
                result = snapshot(ctx, args.date)
            else:
                result = plan(ctx, args.request)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if any(i["severity"] == "error" for i in result.get("issues", [])) else 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"error": str(exc), "executed": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
