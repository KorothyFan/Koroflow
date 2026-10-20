"""Verify the installable skill and source-only plugin archive in isolated directories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get("KORO_TEST_NODE") or shutil.which("node")


@unittest.skipUnless(NODE, "Node >=22.15 is required for repository installation and bundling")
class DistributionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="koro-distribution-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {**os.environ, "CODEX_HOME": str(self.root / "codex")}

    def node(self, script, *args, cwd=ROOT):
        result = subprocess.run([NODE, str(script), *map(str, args)], cwd=cwd, env=self.env,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_operations_only_install_needs_no_hypit_and_preserves_other_skills(self):
        existing = self.root / "codex/skills/video-director/SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("user's existing director", encoding="utf-8")
        self.node(ROOT / "scripts/workflow.mjs", "install-skill", "--operations-only")
        skill = self.root / "codex/skills/koro-operations"
        index = json.loads((skill / "references/local-setup.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(index["operationsScript"]), skill / "scripts/operations.py")
        self.assertEqual(existing.read_text(encoding="utf-8"), "user's existing director")
        self.assertFalse(list(skill.rglob("__pycache__")))
        config = self.root / "local/config.json"
        result = subprocess.run([sys.executable, "-X", "utf8", str(skill / "scripts/operations.py"), "init",
                                 "--config", str(config), "--workspace", str(self.root / "workspace")],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(config.read_text(encoding="utf-8"))["format"], "koro.operations@1")

    def test_core_only_install_is_self_contained_and_preserves_other_skills(self):
        self.node(ROOT / "scripts/workflow.mjs", "install-skill", "--core-only")
        skill = self.root / "codex/skills/koroflow"
        workspace = self.root / "workspace"
        call = subprocess.run([sys.executable, "-X", "utf8", str(skill / "scripts/workflow.py"),
            "--workspace", str(workspace), "init"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(call.returncode, 0, call.stderr)
        self.assertTrue(json.loads(call.stdout)["initialized"])
        self.assertFalse((self.root / "codex/skills/hypit").exists())

    def test_source_zip_contains_plugin_and_runs_after_extraction(self):
        archive = self.root / "bundle.zip"
        self.node(ROOT / "scripts/bundle.mjs", archive)
        with zipfile.ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            names = z.namelist()
            self.assertTrue(any(n.endswith("/plugin.json") for n in names))
            self.assertTrue(any(n.endswith("/.agents/plugins/marketplace.json") for n in names))
            for name in names:
                parts = Path(name).parts
                self.assertFalse({".local", "node_modules", "__pycache__", ".git", ".hypit", ".koroflow"}.intersection(parts), name)
                self.assertFalse(name.endswith(("local-setup.json", ".pyc", ".mp4", ".wav", "tokens.json")), name)
            z.extractall(self.root / "unpacked")
        extracted = self.root / "unpacked/hypit-haiyi-workflow"
        manifest = json.loads((extracted / "plugin.json").read_text(encoding="utf-8"))
        package = json.loads((extracted / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], package["version"])
        catalog = json.loads((extracted / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        entry = catalog["plugins"][0]
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual((extracted / entry["source"]["path"]).resolve(), extracted.resolve())
        self.node(extracted / "scripts/workflow.mjs", "install-skill", "--operations-only", cwd=extracted)
        result = subprocess.run([sys.executable, "-X", "utf8", str(extracted / "scripts/operations.py"), "--help"],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plan", result.stdout)
        self.node(extracted / "scripts/workflow.mjs", "install-skill", "--core-only", cwd=extracted)
        call = subprocess.run([sys.executable, "-X", "utf8", str(extracted / "scripts/koroflow.py"),
            "--workspace", str(self.root / "workspace"), "init"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(call.returncode, 0, call.stderr)
        self.assertTrue(json.loads(call.stdout)["initialized"])


if __name__ == "__main__":
    unittest.main()
