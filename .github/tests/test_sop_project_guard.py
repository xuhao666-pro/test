import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "sop_project_guard.py"
SPEC = importlib.util.spec_from_file_location("sop_project_guard", SCRIPT)
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(guard)


class ProjectGuardTests(unittest.TestCase):
    def write_system(self, root: Path, **changes):
        value = {
            "schema_version": "1.0",
            "lifecycle": "bootstrap",
            "project_initialized": False,
            "project_data_included": False,
            "capabilities": {"dashboard": False},
        }
        value.update(changes)
        path = root / ".github" / "sop-system.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_bootstrap_is_successful_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_system(root)
            self.assertEqual(guard.evaluate(root, ["dashboard"]), (False, "system-bootstrap"))

    def test_disabled_capability_is_successful_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_system(
                root,
                lifecycle="active",
                project_initialized=True,
                project_data_included=True,
            )
            self.assertEqual(
                guard.evaluate(root, ["dashboard"]),
                (False, "capability-disabled:dashboard"),
            )

    def test_active_requires_valid_project_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_system(
                root,
                lifecycle="active",
                project_initialized=True,
                project_data_included=True,
                capabilities={"dashboard": True},
            )
            with self.assertRaises(guard.GuardError):
                guard.evaluate(root, ["dashboard"])
            state = root / "sop" / "project-state.yaml"
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps({"project": {"id": "project-demo"}}), encoding="utf-8")
            self.assertEqual(guard.evaluate(root, ["dashboard"]), (True, "active"))

    def test_unknown_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_system(root, schema_version="2.0")
            with self.assertRaises(guard.GuardError):
                guard.evaluate(root, [])


if __name__ == "__main__":
    unittest.main()
