import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).with_name("sop_issue_notifier.py")
SPEC = importlib.util.spec_from_file_location("sop_issue_notifier", MODULE_PATH)
notifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notifier)


ASSIGNMENT = {
    "assignment_id": "A-02-B02-R3-member-a-prototype-validation",
    "member_id": "member-a",
    "human_owner": "Member A",
    "git_branch": "sop/member/member-a",
}
CONFIG = {
    "enabled": True,
    "coordinator_github_login": "coordinator-user",
    "members": {
        "member-a": {"enabled": True, "github_login": "member-user"}
    },
}


class FakeGitHubClient:
    comment_already_exists = False

    def __init__(self, repository, token):
        self.issue = {
            "number": 25,
            "body": notifier.issue_marker(ASSIGNMENT["assignment_id"]),
            "labels": [{"name": "sop-task"}, {"name": "dispatched"}],
        }
        self.requests = []

    def ensure_labels(self, labels):
        return None

    def find_issue(self, marker):
        return self.issue

    def comment_exists(self, number, marker):
        return self.comment_already_exists

    def request(self, method, path, payload=None):
        self.requests.append((method, path, payload))
        return self.issue


class IssueNotifierTests(unittest.TestCase):
    def test_task_reminder_keeps_existing_state_label(self):
        labels = notifier.transition_labels(["sop-task", "dispatched"], "task-reminder")
        self.assertEqual(labels, ["dispatched", "sop-task"])

    def test_task_reminder_mentions_member_and_uses_explicit_identity(self):
        first = notifier.render_event(
            "task-reminder",
            ASSIGNMENT,
            member_login="member-user",
            coordinator_login="coordinator-user",
            commit_sha="a" * 40,
            assignment_path="sop/stages/02/dispatch/task.yaml",
            run_url="https://github.example/actions/4",
            event_identity="2026-07-20",
        )
        second = notifier.render_event(
            "task-reminder",
            ASSIGNMENT,
            member_login="member-user",
            coordinator_login="coordinator-user",
            commit_sha="b" * 40,
            assignment_path="sop/stages/02/dispatch/task.yaml",
            run_url="https://github.example/actions/5",
            event_identity="2026-07-20",
        )
        self.assertIn("@member-user", first["body"])
        self.assertEqual(first["marker"], second["marker"])

    def test_delivery_reports_whether_reminder_was_new(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            assignment_path = root / "assignment.yaml"
            config_path = root / "config.yaml"
            assignment_path.write_text(json.dumps(ASSIGNMENT), encoding="utf-8")
            config_path.write_text(json.dumps(CONFIG), encoding="utf-8")
            args = Namespace(
                event="task-reminder",
                assignment=str(assignment_path),
                commit="c" * 40,
                config=str(config_path),
                run_url="https://github.example/actions/6",
                detail="status=missing",
                identity="2026-07-20",
            )
            with mock.patch.object(notifier, "GitHubClient", FakeGitHubClient), mock.patch.dict(
                notifier.os.environ,
                {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_TOKEN": "test-token"},
            ):
                FakeGitHubClient.comment_already_exists = False
                output = io.StringIO()
                with redirect_stdout(output):
                    notifier.deliver(args)
                self.assertTrue(json.loads(output.getvalue())["emitted"])

                FakeGitHubClient.comment_already_exists = True
                output = io.StringIO()
                with redirect_stdout(output):
                    notifier.deliver(args)
                self.assertFalse(json.loads(output.getvalue())["emitted"])


if __name__ == "__main__":
    unittest.main()
