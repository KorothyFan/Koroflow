from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

FORMAT = "koroflow.workspace@1"
RELEASED = {"failed", "cancelled", "skipped"}
TRANSITIONS = {
    "prepared": {"submitted", "result_unknown", "cancelled", "skipped"},
    "submitted": {"running", "result_unknown", "succeeded", "scheduled", "published", "failed"},
    "running": {"result_unknown", "succeeded", "scheduled", "published", "failed"},
    "result_unknown": {"running", "succeeded", "scheduled", "published", "failed", "cancelled"},
    "scheduled": {"published", "result_unknown", "cancelled", "failed"},
}
OPERATIONS = {"video.generate", "video.edit", "image.generate", "audio.generate", "video.compose",
              "publication.publish", "publication.schedule"}


def read(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def stamp(value=None):
    value = value or datetime.now(timezone.utc).isoformat()
    result = datetime.fromisoformat(text(value, "timestamp").replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp requires a timezone offset")
    return result


def sha256(file):
    with Path(file).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    file = directory / "write.lock"
    try:
        descriptor = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError(f"Workspace busy; inspect lock owner before recovery: {file}") from exc
    try:
        os.write(descriptor, json.dumps({"pid": os.getpid(), "created_at": stamp().isoformat()}).encode())
        os.close(descriptor)
        yield
    finally:
        file.unlink(missing_ok=True)


def init(workspace):
    directory = Path(workspace).resolve() / ".koroflow"
    with lock(directory):
        if (directory / "config.json").exists():
            raise ValueError("Workspace already initialized; existing configuration is preserved")
        defaults = read(Path(__file__).parents[2] / "references/defaults.json")
        for name in ("quality", "adapters", "targets"):
            atomic_json(directory / f"{name}.json", defaults[name])
        atomic_json(directory / "config.json", {"format": FORMAT, "timezone": "Asia/Shanghai",
                    "quality": "quality.json", "adapters": "adapters.json", "targets": "targets.json"})
    return {"workspace": str(directory.parent), "initialized": True, "external_execution": False}


class Workspace:
    def __init__(self, workspace):
        self.root = Path(workspace).resolve()
        self.directory = self.root / ".koroflow"
        self.config = read(self.directory / "config.json")
        if self.config.get("format") != FORMAT:
            raise ValueError(f"Expected {FORMAT}")
        self.zone = ZoneInfo(self.config["timezone"])

    def setting(self, key):
        path = Path(self.config[key])
        return read(path if path.is_absolute() else self.directory / path)

    def events(self):
        rows = []
        for path in (self.directory / "events").glob("*.json"):
            event = read(path)
            if event.get("format") != "koroflow.event@1":
                raise ValueError(f"Invalid event format: {path}")
            stamp(event["occurred_at"])
            rows.append(event)
        rows.sort(key=lambda item: item["sequence"])
        if [e["sequence"] for e in rows] != list(range(1, len(rows) + 1)):
            raise ValueError("Event journal sequence is incomplete or duplicated; inspect records")
        return rows

    def commit(self, events, work_id, kind, data, key=None, occurred_at=None):
        # Called only while holding the workspace lock; ordering is independent of wall clock ties.
        if key:
            previous = next((e for e in events if e.get("key") == key), None)
            if previous:
                if previous["work_id"] != work_id or previous["kind"] != kind or previous["data"] != data:
                    raise ValueError("Idempotency key already belongs to different content")
                return {**previous, "reused": True}
        event = {"format": "koroflow.event@1", "event_id": str(uuid.uuid4()), "sequence": len(events) + 1,
                 "work_id": work_id, "kind": kind, "occurred_at": stamp(occurred_at).isoformat(), "data": data}
        if key:
            event["key"] = key
        atomic_json(self.directory / "events" / f'{event["event_id"]}.json', event)
        return event

    def work(self, work_id, events=None):
        events = self.events() if events is None else events
        rows = [e for e in events if e["work_id"] == work_id]
        created = next((e for e in rows if e["kind"] in {"work.created", "work.imported"}), None)
        if not created:
            raise ValueError(f"Unknown work_id: {work_id}")
        work = {**created["data"], "revisions": {}, "reviews": {}, "deliveries": [], "tasks": {},
                "state": "in_progress", "adopted": False}
        imported = created["kind"] == "work.imported"
        if imported:
            legacy = created["data"]["legacy"]
            baseline = legacy["delivery"]
            work["revisions"][baseline["revision_id"]] = baseline
            work["deliveries"].append(baseline)
            work["adopted"] = legacy["adopted"]
            work["state"] = "delivered"
        for event in rows:
            kind, data = event["kind"], event["data"]
            if kind == "revision.registered":
                work["revisions"][data["revision_id"]] = data
                if work["deliveries"]:
                    work["state"] = "revising"
            elif kind == "quality.reviewed":
                work["reviews"][data["revision_id"]] = data
            elif kind == "revision.delivered":
                work["deliveries"].append({**data, "occurred_at": event["occurred_at"], "event_id": event["event_id"]})
                work["state"] = "delivered"
            elif kind == "work.adopted":
                work["adopted"] = True
            elif kind in {"work.paused", "work.cancelled", "work.resumed"}:
                work["state"] = "revising" if kind == "work.resumed" and work["deliveries"] else {
                    "work.paused": "paused", "work.cancelled": "cancelled", "work.resumed": "in_progress"}[kind]
            elif kind == "task.prepared":
                work["tasks"][data["task_key"]] = {**data, "status": "prepared"}
            elif kind == "task.updated":
                work["tasks"][data["task_key"]].update(data)
        if work["deliveries"]:
            work["selected_delivery"] = work["deliveries"][-1]
            work["delivered_on"] = created["data"]["legacy"]["delivered_on"] if imported else min(
                stamp(d["occurred_at"]).astimezone(self.zone).date().isoformat() for d in work["deliveries"])
        return work

    def create(self, manifest):
        for field in ("work_id", "role", "content", "project", "brief"):
            text(manifest.get(field), field)
        project = Path(manifest["project"]).resolve()
        if not project.is_dir():
            raise ValueError("Project must already exist; records do not move or recreate projects")
        data = {field: manifest[field] for field in ("work_id", "role", "content", "brief")}
        data["project"] = str(project)
        data["references"] = manifest.get("references", [])
        if not isinstance(data["references"], list) or not all(isinstance(r, dict) and
                isinstance(r.get("asset"), str) and isinstance(r.get("responsibility"), str) for r in data["references"]):
            raise ValueError("Each reference needs asset and responsibility")
        with lock(self.directory):
            events = self.events()
            if any(e.get("key") == f'work:{data["work_id"]}' for e in events):
                return self.commit(events, data["work_id"], "work.created", data, f'work:{data["work_id"]}')
            if any((project / "项目文件/统计事件").glob("*.json")):
                raise ValueError("Existing project events need explicit import-legacy, not a new work record")
            if (project / "项目文件/发布信息.json").exists():
                raise ValueError("Existing project metadata needs explicit import-legacy, not a new work record")
            for event in events:
                if event["kind"] in {"work.created", "work.imported"} and event["work_id"] != data["work_id"] and event["data"]["project"] == data["project"]:
                    raise ValueError("Project already belongs to another work; use a separate character subproject")
            return self.commit(events, data["work_id"], "work.created", data, f'work:{data["work_id"]}')

    def import_legacy(self, inventory_file, work_id, project):
        source = read(inventory_file)
        matches = [w for w in source.get("works", []) if w["work_id"] == work_id]
        if len(matches) != 1:
            raise ValueError("Import requires one explicit existing work from an operations check report")
        row = matches[0]; project = Path(project).resolve()
        if not project.is_dir():
            raise ValueError("Original project must still exist; import does not restore removed projects")
        if str(project) not in {str(Path(p).resolve()) for p in row["projects"]}:
            raise ValueError("Explicit project is not one of this work's original projects")
        if any(i["severity"] == "error" and (i.get("work_id") == work_id or i.get("identity_unresolved")) for i in source.get("issues", [])):
            raise ValueError("Resolve this work's legacy record errors before import")
        if not row.get("delivered") or row.get("withdrawn") or not row.get("selected_file"):
            raise ValueError("Import supports explicit available legacy deliveries; continue other legacy states with operations")
        file = Path(row["selected_file"]).resolve(); digest = sha256(file)
        if row.get("sha256") and row["sha256"] != digest:
            raise ValueError("Legacy inventory is stale: selected bytes changed")
        if row.get("delivered_on"):
            datetime.strptime(row["delivered_on"], "%Y-%m-%d")
        baseline = {"revision_id": "legacy-import", "file": str(file), "sha256": digest,
                    "title_en": row["title_en"], "hashtags": row["hashtags"],
                    "provenance": "legacy-selected-delivery", "evidence": row.get("selection_evidence", str(inventory_file)),
                    "occurred_at": None, "legacy": True}
        data = {"work_id": work_id, "role": row["role"], "content": row["content"], "project": str(project),
                "brief": "Explicit legacy import; original project BRIEF/TREATMENT/PROGRESS remain authoritative",
                "references": [], "legacy": {"source_inventory": str(Path(inventory_file).resolve()),
                    "delivered_on": row.get("delivered_on"), "adopted": bool(row.get("adopted")), "delivery": baseline}}
        with lock(self.directory):
            events = self.events()
            for event in events:
                if event["kind"] in {"work.created", "work.imported"} and event["work_id"] != work_id and event["data"]["project"] == str(project):
                    raise ValueError("Project already belongs to another work")
            return self.commit(events, work_id, "work.imported", data, f"work:{work_id}")

    def register(self, work_id, revision_id, file, provenance):
        file = Path(file).resolve()
        text(revision_id, "revision_id"); text(provenance, "provenance")
        data = {"revision_id": revision_id, "file": str(file), "sha256": sha256(file), "provenance": provenance}
        with lock(self.directory):
            events = self.events(); self.work(work_id, events)
            return self.commit(events, work_id, "revision.registered", data, f"revision:{work_id}:{revision_id}")

    def review(self, work_id, revision_id, review):
        with lock(self.directory):
            events = self.events(); work = self.work(work_id, events)
            revision = work["revisions"][revision_id]
            if sha256(revision["file"]) != revision["sha256"]:
                raise ValueError("Revision bytes changed; register a new revision before review")
            required = self.setting("quality")["required_checks"]
            if not required or len(set(required)) != len(required):
                raise ValueError("Quality profile needs unique required_checks")
            text(review.get("reviewer"), "reviewer"); text(review.get("evidence"), "review evidence")
            results = review.get("checks", {})
            if not isinstance(results, dict) or not all(value in {"pass", "fail", "not_checked"} for value in results.values()):
                raise ValueError("Review checks use pass, fail or not_checked")
            passed = all(results.get(name) == "pass" for name in required)
            data = {"revision_id": revision_id, "sha256": revision["sha256"], "required_checks": required,
                    "checks": results, "passed": passed, "reviewer": review["reviewer"], "evidence": review["evidence"]}
            return self.commit(events, work_id, "quality.reviewed", data)

    def deliver(self, work_id, revision_id, title_en, hashtags, evidence):
        text(title_en, "title_en"); text(evidence, "delivery evidence")
        if not isinstance(hashtags, list) or not all(isinstance(tag, str) and tag.startswith("#") and len(tag) > 1 for tag in hashtags):
            raise ValueError("hashtags must be a list of #tags")
        with lock(self.directory):
            events = self.events(); work = self.work(work_id, events)
            revision = work["revisions"][revision_id]; review = work["reviews"].get(revision_id)
            required = self.setting("quality")["required_checks"]
            if not review or not review["passed"] or not all(review["checks"].get(name) == "pass" for name in required):
                raise ValueError("Current required quality checks have not passed for this revision")
            if sha256(revision["file"]) != revision["sha256"] or review["sha256"] != revision["sha256"]:
                raise ValueError("Reviewed file changed; cannot deliver unchecked bytes")
            data = {**revision, "title_en": title_en, "hashtags": hashtags, "evidence": evidence}
            return self.commit(events, work_id, "revision.delivered", data, f"delivery:{work_id}:{revision_id}")

    def state(self, work_id, action, evidence):
        text(evidence, "evidence")
        if action not in {"paused", "cancelled", "resumed", "adopted"}:
            raise ValueError("Unknown work action")
        with lock(self.directory):
            events = self.events(); work = self.work(work_id, events)
            data = {"evidence": evidence}
            if action == "adopted":
                if not work["deliveries"]:
                    raise ValueError("Adoption must reference a delivered work")
                data["revision_id"] = work["selected_delivery"]["revision_id"]
            return self.commit(events, work_id, f"work.{action}", data)

    def route(self, operation, requires=(), adapter_id=None):
        if operation not in OPERATIONS:
            raise ValueError("Unknown operation")
        rows = self.setting("adapters")
        if not isinstance(rows, list):
            raise ValueError("Adapters must be a list")
        for row in rows:
            text(row.get("id"), "adapter id")
            if row.get("transport") not in {"api", "mcp", "browser", "cli", "manual"} or row.get("status") not in {"implemented", "external", "manual", "unconfigured"}:
                raise ValueError("Invalid adapter transport or status")
            if not isinstance(row.get("operations"), dict):
                raise ValueError("Adapter operations must be an object")
            for name, spec in row["operations"].items():
                if name not in OPERATIONS or not isinstance(spec, dict):
                    raise ValueError("Invalid adapter operation")
                text(spec.get("handoff"), "adapter handoff")
                if not isinstance(spec.get("capabilities"), list) or not all(isinstance(c, str) for c in spec["capabilities"]):
                    raise ValueError("Adapter capabilities must be a list of strings")
        ids = [row["id"] for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError("Adapter IDs must be unique")
        candidates = []
        for adapter in rows:
            if adapter_id and adapter["id"] != adapter_id:
                continue
            spec = adapter.get("operations", {}).get(operation)
            if not spec or adapter.get("status") == "unconfigured":
                continue
            missing = sorted(set(requires) - set(spec.get("capabilities", [])))
            candidates.append({"adapter_id": adapter["id"], "transport": adapter["transport"],
                "status": adapter["status"], "missing_capabilities": missing,
                "compatible": not missing, "handoff": spec["handoff"], "external_execution": False})
        return {"operation": operation, "requires": list(requires), "candidates": candidates,
                "compatible": any(c["compatible"] for c in candidates), "automatically_selected": False}

    def prepare(self, work_id, task_key, adapter_id, operation, request_file, requires=(), account_id=None):
        text(task_key, "task_key")
        route = self.route(operation, requires, adapter_id)
        if not route["compatible"]:
            raise ValueError("Selected adapter does not support all required capabilities; no fallback submitted")
        request_file = Path(request_file).resolve()
        request = read(request_file)
        if not isinstance(request, dict):
            raise ValueError("Request file must be an object")
        data = {"task_key": task_key, "adapter_id": adapter_id, "operation": operation,
                "request_file": str(request_file), "request_sha256": sha256(request_file), "requires": list(requires)}
        with lock(self.directory):
            events = self.events(); work = self.work(work_id, events)
            if operation.startswith("publication."):
                text(account_id, "stable account_id")
                if not work["deliveries"]:
                    raise ValueError("Only a delivered revision can enter publication")
                delivery = work["selected_delivery"]
                if sha256(delivery["file"]) != delivery["sha256"]:
                    raise ValueError("Selected delivered file changed")
                scheduled = request.get("scheduled_at")
                if operation == "publication.schedule" and (not scheduled or stamp(scheduled) <= datetime.now(timezone.utc)):
                    raise ValueError("Scheduling needs a future timestamp with timezone")
                data.update(account_id=account_id, revision_id=delivery["revision_id"],
                            file=delivery["file"], sha256=delivery["sha256"])
                for event in events:
                    if event["kind"] != "task.prepared" or not event["data"]["operation"].startswith("publication."):
                        continue
                    other = self.work(event["work_id"], events)["tasks"][event["data"]["task_key"]]
                    if event["work_id"] == work_id and other["task_key"] == task_key:
                        continue  # content identity is checked by commit below
                    if other["account_id"] == account_id and other["status"] not in RELEASED and (
                            event["work_id"] == work_id or other["sha256"] == data["sha256"]):
                        raise ValueError("Publication already reserved/submitted/scheduled/published; verify before retry")
            return self.commit(events, work_id, "task.prepared", data, f"task:{work_id}:{task_key}")

    def task_update(self, work_id, task_key, status, evidence, remote_id=None, output=None, cost=None):
        text(evidence, "task evidence")
        with lock(self.directory):
            events = self.events(); work = self.work(work_id, events); task = work["tasks"][task_key]
            if status not in TRANSITIONS.get(task["status"], set()):
                raise ValueError(f'Invalid transition {task["status"]} -> {status}')
            if status == "submitted":
                if sha256(task["request_file"]) != task["request_sha256"]:
                    raise ValueError("Prepared request changed; do not submit a different request under this task key")
                if task["operation"].startswith("publication.") and sha256(task["file"]) != task["sha256"]:
                    raise ValueError("Reserved publication file changed")
            publication = task["operation"].startswith("publication.")
            if (publication and status == "succeeded") or (not publication and status in {"scheduled", "published"}):
                raise ValueError("Publication and generation completion states are distinct")
            remote_id = str(remote_id) if isinstance(remote_id, int) and not isinstance(remote_id, bool) else remote_id
            if remote_id and task.get("remote_id") and remote_id != task["remote_id"]:
                raise ValueError("Remote task identity cannot change; record a separate authorized task")
            remote_id = remote_id or task.get("remote_id")
            if status in {"submitted", "running", "succeeded", "scheduled", "published"}:
                text(remote_id, "remote task/publication ID (manual evidence ID is allowed)")
            data = {"task_key": task_key, "status": status, "evidence": evidence}
            if remote_id:
                data["remote_id"] = remote_id
                for event in events:
                    if event["kind"] == "task.updated" and event["data"].get("remote_id") == remote_id and (
                            event["work_id"] != work_id or event["data"]["task_key"] != task_key):
                        other = self.work(event["work_id"], events)["tasks"][event["data"]["task_key"]]
                        if other["adapter_id"] == task["adapter_id"]:
                            raise ValueError("Remote task ID already belongs to another recorded task")
            if status == "succeeded":
                file = Path(text(output, "successful task output file")).resolve()
                data.update(output_file=str(file), output_sha256=sha256(file))
            if cost is not None:
                if not isinstance(cost, dict) or not isinstance(cost.get("amount"), (int, float)) or isinstance(cost.get("amount"), bool) or not math.isfinite(cost["amount"]) or cost["amount"] < 0:
                    raise ValueError("Cost needs a non-negative amount and explicit unit")
                text(cost.get("unit"), "cost unit")
                data["cost"] = cost
            return self.commit(events, work_id, "task.updated", data)

    def report(self, date):
        day = datetime.strptime(date, "%Y-%m-%d").date()
        events = self.events(); ids = {e["work_id"] for e in events if e["kind"] in {"work.created", "work.imported"}}
        works = [self.work(work_id, events) for work_id in sorted(ids)]
        config = self.setting("targets")
        targets = config.get("date_overrides", {}).get(date, config.get("weekend" if day.weekday() >= 5 else "weekday", {}))
        roles = set(targets) | {w["role"] for w in works}
        def event_day(event):
            return stamp(event["occurred_at"]).astimezone(self.zone).date() == day
        output = []
        for role in sorted(roles):
            role_works = [w for w in works if w["role"] == role]
            first_deliveries = [w for w in role_works if w.get("delivered_on") == date]
            succeeded = {(e["data"].get("remote_id"), w["tasks"][e["data"]["task_key"]]["adapter_id"])
                         for w in role_works for e in events if e["work_id"] == w["work_id"] and e["kind"] == "task.updated"
                         and e["data"]["status"] == "succeeded" and event_day(e)
                         and w["tasks"][e["data"]["task_key"]]["operation"] in {"video.generate", "video.edit"}}
            target = targets.get(role)
            if target is not None and (not isinstance(target, int) or isinstance(target, bool) or target < 0):
                raise ValueError("Daily targets must be non-negative integers")
            output.append({"role": role, "generated": len(succeeded), "delivered": len(first_deliveries),
                "adopted": sum(w["adopted"] for w in first_deliveries),
                "in_progress": sum(not w["deliveries"] and w["state"] == "in_progress" for w in role_works),
                "revising": sum(w["state"] == "revising" for w in role_works), "target": target,
                "remaining": max(target - len(first_deliveries), 0) if target is not None else None})
        return {"date": date, "timezone": self.config["timezone"], "roles": output,
                "coverage": "This workspace journal only; legacy snapshot remains authoritative for unimported history",
                "historical_in_progress": "Current state, not a reconstructed historical snapshot"}

    def bridge(self, work_id):
        # Explicit, repeatable export; no inferred history and no Excel/manual-field mutation.
        with lock(self.directory):
            events = self.events(); work = self.work(work_id, events)
            project = Path(work["project"]); directory = project / "项目文件"
            if not project.is_dir():
                raise ValueError("Original project was removed; bridge does not recreate it")
            metadata = directory / "发布信息.json"
            existing = read(metadata) if metadata.exists() else {}
            if existing.get("work_id", work_id) != work_id or existing.get("role", work["role"]) != work["role"]:
                raise ValueError("Legacy metadata belongs to another work; nothing exported")
            deliveries = work["deliveries"]
            latest = work.get("selected_delivery")
            if latest and sha256(latest["file"]) != latest["sha256"]:
                raise ValueError("Delivered bytes changed; bridge refused")
            exports = []
            mapping = {"work.created": "in_progress", "work.resumed": "in_progress", "work.paused": "paused",
                       "work.cancelled": "cancelled", "revision.delivered": "delivered", "work.adopted": "adopted"}
            for event in events:
                if event["work_id"] != work_id or event["kind"] not in mapping:
                    continue
                data = event["data"]
                row = {"work_id": work_id, "role": work["role"], "title": work["content"],
                       "event": mapping[event["kind"]], "occurred_at": event["occurred_at"],
                       "evidence": data.get("evidence", data.get("brief")), "koroflow_event_id": event["event_id"]}
                if row["event"] in {"delivered", "adopted"}:
                    selected = next(d for d in deliveries if d["revision_id"] == data["revision_id"])
                    row.update(file=os.path.relpath(selected["file"], project), delivered_on=work["delivered_on"])
                target = directory / "统计事件" / f'{event["event_id"]}.json'
                if target.exists() and read(target) != row:
                    raise ValueError("Existing bridge event differs; inspect before retry")
                exports.append((target, row))
            with lock(directory / ".koroflow-bridge"):
                existing = read(metadata) if metadata.exists() else {}
                if existing.get("work_id", work_id) != work_id or existing.get("role", work["role"]) != work["role"]:
                    raise ValueError("Legacy metadata changed identity; nothing exported")
                for target, row in exports:
                    if target.exists() and read(target) != row:
                        raise ValueError("Legacy event changed; nothing exported")
                for target, row in exports:
                    if not target.exists():
                        atomic_json(target, row)
                # Preserve unrelated metadata fields; do not carry stale migration selection into a revision.
                if latest:
                    for key in ("source_file", "source_sha256", "selected_file_at_review"):
                        existing.pop(key, None)
                    atomic_json(metadata, {**existing, "work_id": work_id, "role": work["role"], "content": work["content"],
                        "title_en": latest["title_en"], "hashtags": latest["hashtags"],
                        "updated_at": latest["occurred_at"] or existing.get("updated_at") or stamp().isoformat()})
            return {"work_id": work_id, "exported_event_ids": [row["koroflow_event_id"] for _, row in exports],
                    "statistics_refreshed": False, "manual_ledger_fields_changed": False}
