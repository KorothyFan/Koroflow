"""End-to-end journal and adapter contracts; all files and side effects are isolated."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/koroflow/scripts"))
from koroflow_core.core import Workspace, init, lock, read, atomic_json


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="koroflow-core-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        init(self.root)
        self.ws = Workspace(self.root)
        self.project = self.root / "projects/character-story"
        self.project.mkdir(parents=True)
        self.ws.create({"work_id": "w1", "role": "character", "content": "Gift surprise",
                        "brief": "Isolated fixture, no actual production", "project": str(self.project)})
        self.file = self.project / "output.mp4"
        self.file.write_bytes(b"fixture media bytes")
        self.request = self.root / "request.json"
        atomic_json(self.request, {"prompt": "Fixture", "title_en": "Gift surprise"})

    def approved(self, revision="r1", file=None):
        self.ws.register("w1", revision, file or self.file, "test fixture")
        self.ws.review("w1", revision, {"reviewer": "fixture", "evidence": "Fixture review, not real media QA",
            "checks": {name: "pass" for name in self.ws.setting("quality")["required_checks"]}})

    def delivered(self, revision="r1", file=None):
        self.approved(revision, file)
        return self.ws.deliver("w1", revision, "A tiny surprise", ["#cute"], "Fixture delivery")

    def prepare_publication(self, task="p1", account="account-a"):
        return self.ws.prepare("w1", task, "manual-publication", "publication.publish", self.request, account_id=account)

    def test_project_registration_does_not_create_fake_media_or_delivery(self):
        work = self.ws.work("w1")
        self.assertEqual(work["state"], "in_progress")
        self.assertEqual(work["deliveries"], [])
        self.assertFalse((self.project / "项目文件/发布信息.json").exists())

    def test_quality_gate_blocks_incomplete_review(self):
        self.ws.register("w1", "r1", self.file, "fixture")
        self.ws.review("w1", "r1", {"reviewer": "fixture", "evidence": "Only visual tested",
                                    "checks": {"visual_continuity": "pass"}})
        with self.assertRaises(ValueError):
            self.ws.deliver("w1", "r1", "Title", [], "not a real delivery")

    def test_changed_bytes_require_new_revision_and_review(self):
        self.approved()
        self.file.write_bytes(b"changed after review")
        with self.assertRaises(ValueError):
            self.ws.deliver("w1", "r1", "Title", [], "fixture")
        with self.assertRaises(ValueError):
            self.ws.register("w1", "r1", self.file, "same ID must not change content")

    def test_new_required_check_invalidates_older_review(self):
        self.approved()
        profile = self.ws.setting("quality")
        profile["required_checks"].append("product_accuracy")
        atomic_json(self.ws.directory / "quality.json", profile)
        with self.assertRaises(ValueError):
            self.ws.deliver("w1", "r1", "Title", [], "fixture")

    def test_revisions_and_adoption_do_not_duplicate_daily_delivery(self):
        self.delivered()
        self.ws.state("w1", "adopted", "Explicit user fixture acceptance")
        file2 = self.project / "r2.mp4"; file2.write_bytes(b"second revision")
        self.delivered("r2", file2)
        day = datetime.now(timezone.utc).astimezone(self.ws.zone).date().isoformat()
        report = self.ws.report(day)["roles"][0]
        self.assertEqual((report["delivered"], report["adopted"], report["generated"]), (1, 1, 0))
        self.assertEqual(self.ws.work("w1")["selected_delivery"]["revision_id"], "r2")

    def test_delivery_retry_is_idempotent_and_different_content_rejected(self):
        first = self.delivered()
        second = self.ws.deliver("w1", "r1", "A tiny surprise", ["#cute"], "Fixture delivery")
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertTrue(second["reused"])
        with self.assertRaises(ValueError):
            self.ws.deliver("w1", "r1", "Different publication metadata", [], "fixture")

    def test_local_reservation_prevents_duplicate_across_separate_processes(self):
        self.delivered(); self.prepare_publication()
        process = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/koroflow.py"),
            "--workspace", str(self.root), "prepare", "--work", "w1", "--task", "p2", "--adapter", "manual-publication",
            "--operation", "publication.publish", "--request", str(self.request), "--account", "account-a"],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 2)
        self.assertIn("already reserved", json.loads(process.stderr)["error"])
        self.assertEqual(len(self.ws.work("w1")["tasks"]), 1)

    def test_unknown_result_cannot_be_resubmitted_but_other_account_can(self):
        self.delivered(); self.prepare_publication()
        self.ws.task_update("w1", "p1", "submitted", "submission evidence", remote_id="publication-1")
        self.ws.task_update("w1", "p1", "result_unknown", "connection lost")
        with self.assertRaises(ValueError): self.prepare_publication("p2")
        self.prepare_publication("p3", "account-b")

    def test_lost_submission_receipt_can_be_recovered_without_resubmission(self):
        self.ws.prepare("w1", "v1", "haiyi-hypit", "video.generate", self.request)
        self.ws.task_update("w1", "v1", "result_unknown", "Submission response was lost")
        self.ws.task_update("w1", "v1", "running", "Remote task found by original request", remote_id=1680159)
        with self.assertRaises(ValueError):
            self.ws.task_update("w1", "v1", "succeeded", "Wrong remote identity", remote_id=1680160, output=str(self.file))
        self.ws.task_update("w1", "v1", "succeeded", "Original task output received", output=str(self.file))
        task = self.ws.work("w1")["tasks"]["v1"]
        self.assertEqual(task["remote_id"], "1680159")
        self.assertEqual(task["status"], "succeeded")

    def test_prepared_request_and_publication_file_cannot_change_at_submission(self):
        self.delivered(); self.prepare_publication()
        self.request.write_text('{"prompt": "Changed request"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.ws.task_update("w1", "p1", "submitted", "Fixture", remote_id="p1")
        atomic_json(self.request, {"prompt": "Fixture", "title_en": "Gift surprise"})
        self.file.write_bytes(b"modified publication bytes")
        with self.assertRaises(ValueError):
            self.ws.task_update("w1", "p1", "submitted", "Fixture", remote_id="p1")
        self.assertEqual(self.ws.work("w1")["tasks"]["p1"]["status"], "prepared")

    def test_cost_needs_a_finite_amount_and_explicit_unit(self):
        self.ws.prepare("w1", "v1", "haiyi-hypit", "video.generate", self.request)
        for cost in ({"amount": float("nan"), "unit": "credits"}, {"amount": float("inf"), "unit": "credits"}, {"amount": 1}):
            with self.assertRaises(ValueError):
                self.ws.task_update("w1", "v1", "submitted", "Fixture", remote_id="v1", cost=cost)
        self.ws.task_update("w1", "v1", "submitted", "Fixture", remote_id="v1", cost={"amount": 2.5, "unit": "credits"})
        self.assertEqual(self.ws.work("w1")["tasks"]["v1"]["cost"]["unit"], "credits")

    def test_same_file_under_different_work_ids_is_reserved_once_per_account(self):
        self.delivered(); self.prepare_publication()
        project = self.root / "another-project"; project.mkdir()
        self.ws.create({"work_id": "w2", "role": "character", "content": "Other title", "brief": "Fixture", "project": str(project)})
        self.ws.register("w2", "r1", self.file, "Same file fixture")
        self.ws.review("w2", "r1", {"reviewer": "fixture", "evidence": "Fixture", "checks": {
            name: "pass" for name in self.ws.setting("quality")["required_checks"]}})
        self.ws.deliver("w2", "r1", "Title", [], "Fixture")
        with self.assertRaises(ValueError):
            self.ws.prepare("w2", "p2", "manual-publication", "publication.publish", self.request, account_id="account-a")

    def test_failed_task_release_requires_real_status_transition(self):
        self.delivered(); self.prepare_publication()
        with self.assertRaises(ValueError): self.ws.task_update("w1", "p1", "failed", "No evidence of submission")
        self.ws.task_update("w1", "p1", "submitted", "Fixture submission", remote_id="p1")
        self.ws.task_update("w1", "p1", "failed", "Explicit platform failure")
        self.prepare_publication("p2")

    def test_scheduled_is_not_published_or_adopted(self):
        self.delivered()
        atomic_json(self.request, {"scheduled_at": "2099-01-01T00:00:00+08:00"})
        self.ws.prepare("w1", "p1", "manual-publication", "publication.schedule", self.request, account_id="account-a")
        self.ws.task_update("w1", "p1", "submitted", "Fixture", remote_id="p1")
        self.ws.task_update("w1", "p1", "scheduled", "Scheduled list evidence")
        self.assertFalse(self.ws.work("w1")["adopted"])
        self.assertEqual(self.ws.work("w1")["tasks"]["p1"]["status"], "scheduled")

    def test_video_success_counts_once_and_audio_or_composition_does_not(self):
        for task, adapter, operation in [("v1", "haiyi-hypit", "video.generate"), ("a1", "haiyi-skill", "audio.generate"), ("c1", "hypit-local", "video.compose")]:
            self.ws.prepare("w1", task, adapter, operation, self.request)
            self.ws.task_update("w1", task, "submitted", "Fixture", remote_id=task)
            self.ws.task_update("w1", task, "succeeded", "Output file received", output=str(self.file))
        day = datetime.now(timezone.utc).astimezone(self.ws.zone).date().isoformat()
        self.assertEqual(self.ws.report(day)["roles"][0]["generated"], 1)
        self.assertFalse(self.ws.work("w1")["deliveries"])

    def test_duplicate_remote_task_receipt_is_not_another_generation(self):
        for task in ("v1", "v2"): self.ws.prepare("w1", task, "haiyi-hypit", "video.generate", self.request)
        self.ws.task_update("w1", "v1", "submitted", "Fixture", remote_id=123)
        with self.assertRaises(ValueError): self.ws.task_update("w1", "v2", "submitted", "Same remote task", remote_id=123)

    def test_missing_capability_or_unconfigured_canvas_does_not_fallback(self):
        route = self.ws.route("video.generate", ["unsupported-motion-control"], "haiyi-hypit")
        self.assertFalse(route["compatible"])
        with self.assertRaises(ValueError):
            self.ws.prepare("w1", "v1", "haiyi-hypit", "video.generate", self.request, ["unsupported-motion-control"])
        adapters = self.ws.setting("adapters")
        adapters.append(read(ROOT / "skills/koroflow/assets/templates/adapter.example.json"))
        atomic_json(self.ws.directory / "adapters.json", adapters)
        self.assertFalse(self.ws.route("video.generate", adapter_id="my-canvas-platform")["compatible"])

    def test_configured_mcp_adapter_can_handoff_without_core_network_execution(self):
        adapters = self.ws.setting("adapters")
        adapter = read(ROOT / "skills/koroflow/assets/templates/adapter.example.json")
        adapter["status"] = "external"; adapters.append(adapter)
        atomic_json(self.ws.directory / "adapters.json", adapters)
        prepared = self.ws.prepare("w1", "canvas-1", adapter["id"], "video.generate", self.request, ["reference_image"])
        self.assertEqual(prepared["kind"], "task.prepared")
        self.assertFalse(self.ws.route("video.generate", adapter_id=adapter["id"])["automatically_selected"])

    def test_begin_and_deliver_bridge_is_repeatable_and_preserves_manual_metadata(self):
        self.ws.bridge("w1")
        directory = self.project / "项目文件"
        self.assertEqual(len(list((directory / "统计事件").glob("*.json"))), 1)
        self.delivered()
        atomic_json(directory / "发布信息.json", {"work_id": "w1", "role": "character", "operator_note": "keep me", "source_sha256": "stale"})
        self.ws.bridge("w1"); first = {p.name: p.read_bytes() for p in (directory / "统计事件").glob("*.json")}
        self.ws.bridge("w1"); second = {p.name: p.read_bytes() for p in (directory / "统计事件").glob("*.json")}
        self.assertEqual(first, second)
        meta = read(directory / "发布信息.json")
        self.assertEqual(meta["operator_note"], "keep me"); self.assertNotIn("source_sha256", meta)
        self.assertEqual(meta["title_en"], "A tiny surprise")

    def test_bridge_roundtrip_is_readable_by_legacy_operations(self):
        self.delivered()
        self.ws.state("w1", "adopted", "Explicit fixture acceptance")
        self.ws.bridge("w1")
        spec = importlib.util.spec_from_file_location("bridge_operations", ROOT / "skills/koro-operations/scripts/operations.py")
        ops = importlib.util.module_from_spec(spec); spec.loader.exec_module(ops)
        config = self.root / "legacy-operations.json"
        atomic_json(config, {"format": ops.FORMAT, "timezone": "Asia/Shanghai", "paths": {"projects": "projects"}})
        inventory = ops.inventory(ops.Context(config), hash_files=True)
        self.assertEqual(inventory["issues"], [])
        selected = inventory["works"][0]
        self.assertEqual(selected["work_id"], "w1")
        self.assertEqual(selected["selected_file"], str(self.file.resolve()))
        self.assertTrue(selected["adopted"])
        self.assertEqual(selected["delivered_on"], self.ws.work("w1")["delivered_on"])
        atomic_json(self.root / "inventory.json", inventory)
        second = self.root / "second-workspace"; init(second)
        imported = Workspace(second)
        imported.import_legacy(self.root / "inventory.json", "w1", self.project)
        self.assertEqual(imported.work("w1")["delivered_on"], selected["delivered_on"])
        self.assertTrue(imported.work("w1")["adopted"])

    def test_existing_work_does_not_get_new_work_id_or_new_delivery_date(self):
        legacy = self.root / "legacy"; legacy.mkdir()
        (legacy / "项目文件/统计事件").mkdir(parents=True)
        atomic_json(legacy / "项目文件/统计事件/old.json", {"existing": True})
        with self.assertRaises(ValueError):
            self.ws.create({"work_id": "w2", "role": "character", "content": "Old", "brief": "Fixture", "project": str(legacy)})
        inventory = self.root / "inventory.json"
        atomic_json(inventory, {"works": [{"work_id": "w2", "role": "character", "content": "Old", "projects": [str(legacy)],
            "selected_file": str(self.file), "delivered": True, "adopted": False, "delivered_on": None,
            "title_en": "Old title", "hashtags": []}], "issues": []})
        self.ws.import_legacy(inventory, "w2", legacy)
        self.ws.register("w2", "new", self.file, "Fixture revision")
        self.ws.review("w2", "new", {"reviewer": "fixture", "evidence": "Fixture", "checks": {
            name: "pass" for name in self.ws.setting("quality")["required_checks"]}})
        self.ws.deliver("w2", "new", "Revision", [], "Fixture")
        self.assertIsNone(self.ws.work("w2")["delivered_on"])

    def test_lock_contention_fails_without_overwriting_owner(self):
        with lock(self.ws.directory):
            before = (self.ws.directory / "write.lock").read_bytes()
            with self.assertRaises(ValueError): self.ws.state("w1", "paused", "Fixture")
            self.assertEqual(before, (self.ws.directory / "write.lock").read_bytes())

    def test_import_cannot_bind_another_work_to_an_existing_project(self):
        inventory = self.root / "inventory.json"
        atomic_json(inventory, {"works": [{"work_id": "w2", "role": "character", "content": "Other",
            "projects": [str(self.project)], "selected_file": str(self.file), "delivered": True,
            "title_en": "Old title", "hashtags": []}], "issues": []})
        with self.assertRaises(ValueError): self.ws.import_legacy(inventory, "w2", self.project)

    def test_bridge_does_not_restore_a_removed_project(self):
        self.file.unlink(); self.project.rmdir()
        with self.assertRaises(ValueError): self.ws.bridge("w1")
        self.assertFalse(self.project.exists())

    def test_metadata_only_legacy_project_is_not_registered_as_new(self):
        project = self.root / "metadata-only"; project.mkdir()
        atomic_json(project / "项目文件/发布信息.json", {"work_id": "old"})
        with self.assertRaises(ValueError):
            self.ws.create({"work_id": "new", "role": "character", "content": "Old",
                "brief": "Fixture", "project": str(project)})

    def test_missing_event_is_detected(self):
        self.ws.state("w1", "paused", "Fixture")
        first = self.ws.events()[0]
        (self.ws.directory / "events" / f'{first["event_id"]}.json').unlink()
        with self.assertRaises(ValueError): self.ws.events()

    def test_targets_are_configured_and_role_surplus_does_not_offset_gap(self):
        self.delivered()
        day = datetime.now(timezone.utc).astimezone(self.ws.zone).date().isoformat()
        atomic_json(self.ws.directory / "targets.json", {"date_overrides": {day: {"character": 0, "another": 2}}})
        rows = {r["role"]: r for r in self.ws.report(day)["roles"]}
        self.assertEqual(rows["character"]["remaining"], 0)
        self.assertEqual(rows["another"]["remaining"], 2)


if __name__ == "__main__": unittest.main()
