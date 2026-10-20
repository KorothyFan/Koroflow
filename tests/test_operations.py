"""Behavior tests use temporary projects only; no platform, credentials or production writes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("operations", ROOT / "skills/koro-operations/scripts/operations.py")
ops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ops)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class OperationsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="koro-operations-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.projects = self.root / "视频项目"
        self.projects.mkdir()
        self.history = self.root / "发布任务"
        self.history.mkdir()
        self.config = self.root / "config.json"
        self.registry = self.root / "accounts.json"
        write(self.registry, {"accounts": [
            {"account_id": "a", "window": "1-1", "role": "企鹅", "tiktok_username": "sample_a"},
            {"account_id": "b", "window": "1-1", "role": "企鹅", "tiktok_username": "sample_b"}]})
        write(self.config, {"format": ops.FORMAT, "timezone": "Asia/Shanghai", "paths": {
            "projects": "视频项目", "publishing_accounts": "accounts.json", "publication_tasks": "发布任务"}})
        self.ctx = ops.Context(self.config)

    def project(self, name="one", work_id="w1", role="企鹅", file_content=b"sample video bytes"):
        project = self.projects / name
        file = project / "成片输出/final.mp4"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(file_content)
        write(project / "项目文件/发布信息.json", {"work_id": work_id, "role": role,
              "content": "测试剧情", "title_en": "Tiny delivery", "hashtags": ["#cute"], "updated_at": "2026-10-19T09:00:00+08:00"})
        self.event(project, "01", work_id=work_id, role=role)
        return project

    def event(self, project, name, **changes):
        value = {"work_id": "w1", "role": "企鹅", "event": "delivered", "evidence": "Test delivery",
                 "occurred_at": "2026-10-19T10:00:00+08:00", "delivered_on": "2026-10-19", "file": "成片输出/final.mp4"}
        value.update(changes)
        write(project / f"项目文件/统计事件/{name}.json", value)

    def request(self, **changes):
        row = {"work_id": "w1", "account_id": "a", "scheduled_at": "2099-10-20T00:00:00+08:00"}
        row.update(changes)
        file = self.root / "request.json"
        write(file, {"items": [row]})
        return file

    def codes(self, result):
        return {i["code"] for i in result["issues"] if i["severity"] == "error"}

    def test_revisions_merge_and_latest_delivery_is_selected(self):
        first = self.project()
        second = self.project("revision")
        self.event(second, "01", occurred_at="2026-10-20T10:00:00+08:00", delivered_on="2026-10-19")
        self.event(second, "02", event="in_progress", occurred_at="2026-10-20T11:00:00+08:00")
        result = ops.inventory(self.ctx)
        self.assertEqual(result["summary"]["delivered"], 1)
        self.assertEqual(result["summary"]["revising"], 1)
        self.assertEqual(result["summary"]["in_progress"], 0)
        self.assertEqual(result["works"][0]["selected_file"], str((second / "成片输出/final.mp4").resolve()))
        self.assertEqual(result["works"][0]["delivered_on"], "2026-10-19")
        self.assertTrue((first / "成片输出/final.mp4").exists())

    def test_folder_name_does_not_imply_adoption(self):
        self.project("已发布/sample")
        result = ops.inventory(self.ctx)
        self.assertEqual(result["summary"]["adopted"], 0)

    def test_adoption_needs_evidence_and_does_not_invent_delivery_date(self):
        project = self.project()
        self.event(project, "01", event="adopted", delivered_on=None, evidence="User accepted")
        result = ops.inventory(self.ctx)
        self.assertTrue(result["works"][0]["adopted"])
        self.assertIsNone(result["works"][0]["delivered_on"])
        self.event(project, "01", event="adopted", evidence="")
        self.assertIn("invalid_event", self.codes(ops.inventory(self.ctx)))

    def test_missing_latest_file_never_falls_back(self):
        project = self.project()
        self.event(project, "02", occurred_at="2026-10-20T10:00:00+08:00", file="成片输出/missing.mp4")
        result = ops.plan(self.ctx, self.request())
        self.assertIn("missing_delivery_file", self.codes(result))
        self.assertFalse(result["preflight_ok"])
        self.assertEqual(result["items"], [])

    def test_plan_is_read_only_and_separates_target_accounts(self):
        self.project()
        targets = self.root / "targets.json"
        write(targets, {"accounts": [{"account": "production-only", "daily_target": 42}]})
        cfg = ops.read_json(self.config)
        cfg["paths"]["production_targets"] = "targets.json"
        write(self.config, cfg)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        request = self.request()
        before[request.relative_to(self.root)] = request.read_bytes()
        result = ops.plan(ops.Context(self.config), request)
        self.assertTrue(result["preflight_ok"])
        self.assertFalse(result["executed"])
        self.assertFalse(result["reserved"])
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["items"][0]["account_id"], "a")

    def test_unrelated_legacy_missing_file_does_not_block_valid_candidate(self):
        self.project()
        other = self.project("old", "w2")
        (other / "成片输出/final.mp4").unlink()
        result = ops.plan(self.ctx, self.request())
        self.assertTrue(result["preflight_ok"])
        self.assertTrue(any(i["code"] == "missing_delivery_file" and i["outside_request"] for i in result["issues"]))
        check = ops.inventory(self.ctx)
        self.assertIn("missing_delivery_file", self.codes(check))
        self.assertEqual(check["summary"]["available_deliveries"], 1)

    def test_event_role_conflict_blocks_candidate(self):
        project = self.project()
        self.event(project, "02", role="wrong-character", occurred_at="2026-10-20T10:00:00+08:00")
        self.assertIn("invalid_event", self.codes(ops.plan(self.ctx, self.request())))

    def test_stable_id_disambiguates_identical_windows(self):
        self.project()
        result = ops.plan(self.ctx, self.request(account_id="1-1"))
        self.assertIn("unknown_plan_identity", self.codes(result))
        self.assertTrue(ops.plan(self.ctx, self.request(account_id="b"))["preflight_ok"])

    def test_scheduled_and_unknown_results_block_same_account_retry(self):
        self.project()
        request = self.request()
        for status in ("scheduled", "result_unknown", "published", "unrecognized-state"):
            with self.subTest(status=status):
                write(self.history / "prior.json", {"tiktok_username": "sample_a", "items": [{"work_id": "w1", "status": status}]})
                self.assertIn("already_assigned_or_published", self.codes(ops.plan(self.ctx, request)))
        self.assertTrue(ops.plan(self.ctx, self.request(account_id="b"))["preflight_ok"])

    def test_skipped_task_releases_work(self):
        self.project()
        write(self.history / "prior.json", {"window": "1-1", "items": [{"work_id": "w1", "status": "skipped"}]})
        self.assertTrue(ops.plan(self.ctx, self.request())["preflight_ok"])

    def test_legacy_bitbrowser_record_and_same_hash_are_detected(self):
        project = self.project()
        write(self.history / "legacy.json", {"videos": [{"record_id": "work:another-id", "username": "sample_a", "status": "published",
                                                       "scheduled_at": "2026-10-20T00:00:00+08:00", "sha256": ops.digest(project / "成片输出/final.mp4")}]})
        self.assertIn("already_assigned_or_published", self.codes(ops.plan(self.ctx, self.request())))

    def test_accounts_with_unknown_usernames_do_not_break_history_matching(self):
        self.project()
        rows = ops.read_json(self.registry)
        rows["accounts"].append({"account_id": "offline", "window": "2-2", "role": "企鹅", "tiktok_username": None})
        write(self.registry, rows)
        write(self.history / "prior.json", {"tiktok_username": "sample_a", "items": [{"work_id": "w1", "status": "published"}]})
        result = ops.plan(self.ctx, self.request())
        self.assertNotIn("invalid_publication_history", self.codes(result))
        self.assertIn("already_assigned_or_published", self.codes(result))

    def test_unknown_history_identity_only_blocks_related_work(self):
        self.project()
        write(self.history / "unknown.json", {"items": [{"work_id": "unrelated", "status": "published"}]})
        self.assertTrue(ops.plan(self.ctx, self.request())["preflight_ok"])
        write(self.history / "unknown.json", {"items": [{"work_id": "w1", "status": "submitted"}]})
        self.assertIn("unresolved_history_account", self.codes(ops.plan(self.ctx, self.request())))

    def test_duplicate_files_under_different_work_ids(self):
        self.project()
        self.project("two", "w2")
        request = self.request()
        data = ops.read_json(request)
        data["items"].append({"work_id": "w2", "account_id": "a"})
        write(request, data)
        self.assertIn("duplicate_file_in_request", self.codes(ops.plan(self.ctx, request)))

    def test_logged_out_and_wrong_role_block_plan(self):
        self.project(role="菲比")
        cfg = ops.read_json(self.config)
        cfg["paths"]["account_snapshot"] = "login.json"
        write(self.config, cfg)
        write(self.root / "login.json", {"checked_at": "2026-10-20T12:00:00+08:00", "excluded_accounts": [{"window": "1-1", "device_ip": "example-ip", "status": "logged out"}]})
        rows = ops.read_json(self.registry)
        rows["accounts"][0].update(device_ip="example-ip", status="logged_out")
        write(self.registry, rows)
        result = ops.plan(ops.Context(self.config), self.request())
        self.assertIn("unavailable_account", self.codes(result))
        self.assertIn("role_mismatch", self.codes(result))

    def test_naive_or_past_schedule_is_rejected(self):
        self.project()
        for value in ("2099-10-20T00:00:00", "2000-01-01T00:00:00+08:00", "not-a-date"):
            with self.subTest(value=value):
                self.assertIn("invalid_schedule", self.codes(ops.plan(self.ctx, self.request(scheduled_at=value))))

    def test_snapshot_preserves_original_time_and_confirmed_minimum(self):
        file = self.root / "snapshot.json"
        write(file, {"updated_at": "2026-10-19T17:00:00+08:00", "summary": {"generated": 3, "delivered": 2, "adopted": 1},
                     "production_targets": [{"date": "2026-10-19", "confirmed_minimum": 4, "completed": 4}]})
        cfg = ops.read_json(self.config)
        cfg["paths"]["statistics_snapshot"] = "snapshot.json"
        write(self.config, cfg)
        result = ops.snapshot(ops.Context(self.config), "2026-10-19")
        self.assertFalse(result["refreshed"])
        self.assertEqual(result["updated_at"], "2026-10-19T17:00:00+08:00")
        self.assertEqual(result["production_targets"][0]["confirmed_minimum"], 4)

    def test_init_refuses_overwrite_and_cli_errors_are_structured(self):
        original = self.config.read_bytes()
        with self.assertRaises(FileExistsError):
            ops.init_config(self.config, self.root)
        self.assertEqual(original, self.config.read_bytes())
        call = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/operations.py"), "doctor", "--config", str(self.root / "missing")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(call.returncode, 2)
        self.assertFalse(json.loads(call.stderr)["executed"])

    def test_hash_only_publication_history_blocks_same_file(self):
        project = self.project()
        write(self.history / "prior.json", {"account_id": "a", "items": [{
            "sha256": ops.digest(project / "成片输出/final.mp4"), "status": "published"}]})
        self.assertIn("already_assigned_or_published", self.codes(ops.plan(self.ctx, self.request())))

    def test_new_delivery_without_file_blocks_old_selection(self):
        project = self.project()
        self.event(project, "02", occurred_at="2026-10-20T10:00:00+08:00", file=None)
        self.assertFalse(ops.plan(self.ctx, self.request())["preflight_ok"])

    def test_invalid_revision_metadata_still_belongs_to_requested_work(self):
        self.project()
        revision = self.project("revision")
        meta_file = revision / "项目文件/发布信息.json"
        meta = ops.read_json(meta_file)
        del meta["hashtags"]
        write(meta_file, meta)
        result = ops.plan(self.ctx, self.request())
        self.assertFalse(result["preflight_ok"])
        self.assertIn("invalid_metadata", self.codes(result))

    def test_unreadable_metadata_identity_is_not_silently_ignored(self):
        self.project()
        bad = self.projects / "bad/项目文件/发布信息.json"
        bad.parent.mkdir(parents=True)
        bad.write_text("{invalid", encoding="utf-8")
        self.assertFalse(ops.plan(self.ctx, self.request())["preflight_ok"])


if __name__ == "__main__":
    unittest.main()
