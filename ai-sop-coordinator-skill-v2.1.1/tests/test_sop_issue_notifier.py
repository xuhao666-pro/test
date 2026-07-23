import importlib.util
import pathlib
import json
import tempfile
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).parents[1]
    / "ai-sop-coordinator"
    / "assets"
    / "github-notifications"
    / "sop_issue_notifier.py"
)
SPEC = importlib.util.spec_from_file_location("sop_issue_notifier", MODULE_PATH)
notifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notifier)


ASSIGNMENT = {
    "assignment_id": "A-02-B01-R2-xiaogao-system-inventory",
    "member_id": "xiaogao",
    "summary": "Inventory the current system",
    "git_branch": "sop/member/xiaogao",
    "minimum_skill_version": "1.7.5",
}


class NotifierTests(unittest.TestCase):
    def test_validates_github_login(self):
        self.assertEqual(notifier.validate_github_login("octo-user"), "octo-user")
        for value in ("", "@octo", "two words", "bad/name", "-leading"):
            with self.subTest(value=value), self.assertRaises(notifier.NotificationError):
                notifier.validate_github_login(value)

    def test_markers_are_stable_and_commit_bound(self):
        issue = notifier.issue_marker(ASSIGNMENT["assignment_id"])
        first = notifier.event_marker(ASSIGNMENT["assignment_id"], "submission-valid", "abc123")
        again = notifier.event_marker(ASSIGNMENT["assignment_id"], "submission-valid", "abc123")
        changed = notifier.event_marker(ASSIGNMENT["assignment_id"], "submission-valid", "def456")
        self.assertIn(ASSIGNMENT["assignment_id"], issue)
        self.assertEqual(first, again)
        self.assertNotEqual(first, changed)

    def test_dispatch_mentions_member_and_preserves_exact_fact_links(self):
        rendered = notifier.render_event(
            "task-dispatched",
            ASSIGNMENT,
            member_login="xiaogao-gh",
            coordinator_login="coord-gh",
            commit_sha="a" * 40,
            assignment_path="sop/stages/02/dispatch/task.yaml",
            run_url="https://github.example/actions/1",
        )
        self.assertEqual(rendered["title"], "[SOP 新任务] A-02-B01-R2-xiaogao-system-inventory")
        self.assertIn("@xiaogao-gh", rendered["body"])
        self.assertIn("sop/member/xiaogao", rendered["body"])
        self.assertIn("a" * 40, rendered["body"])
        self.assertEqual(rendered["labels"], ["sop-task", "dispatched"])

    def test_submission_events_use_precise_language_and_mentions(self):
        cases = {
            "submission-received": ("@coord-gh", "待可信校验", "pending-validation"),
            "submission-valid": ("@coord-gh", "可信校验通过", "valid"),
            "submission-invalid": ("@xiaogao-gh @coord-gh", "可信校验失败", "invalid"),
            "task-blocked": ("@coord-gh", "报告阻塞", "blocked"),
        }
        for event, (mention, phrase, label) in cases.items():
            with self.subTest(event=event):
                rendered = notifier.render_event(
                    event,
                    ASSIGNMENT,
                    member_login="xiaogao-gh",
                    coordinator_login="coord-gh",
                    commit_sha="b" * 40,
                    assignment_path="sop/stages/02/dispatch/task.yaml",
                    run_url="https://github.example/actions/2",
                    detail="safe summary",
                )
                self.assertIn(mention, rendered["body"])
                self.assertIn(phrase, rendered["body"])
                self.assertIn(label, rendered["labels"])

    def test_unknown_event_is_rejected(self):
        with self.assertRaises(notifier.NotificationError):
            notifier.render_event(
                "issue-command",
                ASSIGNMENT,
                member_login="xiaogao-gh",
                coordinator_login="coord-gh",
                commit_sha="c" * 40,
                assignment_path="task.yaml",
                run_url="https://github.example/actions/3",
            )

    def test_label_transition_never_downgrades_valid(self):
        self.assertEqual(
            notifier.transition_labels(["sop-task", "valid"], "submission-received"),
            ["sop-task", "valid"],
        )
        self.assertEqual(
            notifier.transition_labels(["sop-task", "pending-validation"], "submission-invalid"),
            ["sop-task", "invalid"],
        )

    def test_sanitizes_detail(self):
        rendered = notifier.render_event(
            "submission-invalid",
            ASSIGNMENT,
            member_login="xiaogao-gh",
            coordinator_login="coord-gh",
            commit_sha="d" * 40,
            assignment_path="task.yaml",
            run_url="https://github.example/actions/4",
            detail="token=secret\nsecond line",
        )
        self.assertNotIn("secret", rendered["body"])
        self.assertIn("[redacted]", rendered["body"])

    def test_discovers_dispatch_and_exact_member_commit_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            dispatch = root / "sop/stages/02/dispatch/task.yaml"
            dispatch.parent.mkdir(parents=True)
            dispatch.write_text(json.dumps(ASSIGNMENT), encoding="utf-8")
            state = root / "sop/project-state.yaml"
            state.write_text(
                json.dumps(
                    {
                        "submission_tracking": {
                            "stages": {
                                "02": {
                                    "records": {
                                        ASSIGNMENT["assignment_id"]: {
                                            **ASSIGNMENT,
                                            "observed_head": "e" * 40,
                                            "status": "submitted",
                                            "validation_status": "valid",
                                        }
                                    }
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            main_events = notifier.discover_events(
                root, "refs/heads/main", "f" * 40, [dispatch.relative_to(root).as_posix()]
            )
            member_events = notifier.discover_events(
                root, "refs/heads/sop/member/xiaogao", "e" * 40, []
            )
            self.assertEqual([item["event"] for item in main_events], ["task-dispatched"])
            self.assertEqual(
                [item["event"] for item in member_events],
                ["submission-received", "submission-valid"],
            )


if __name__ == "__main__":
    unittest.main()
