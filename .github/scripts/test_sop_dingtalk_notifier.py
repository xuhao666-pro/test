import base64
import hashlib
import hmac
import importlib.util
import json
import pathlib
import unittest
import urllib.parse
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).with_name("sop_dingtalk_notifier.py")
SPEC = importlib.util.spec_from_file_location("sop_dingtalk_notifier", MODULE_PATH)
notifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notifier)

ASSIGNMENT = {
    "assignment_id": "A-02-B01-R2-member-a-review",
    "member_id": "member-a",
    "human_owner": "Member A",
}


class DingTalkNotifierTests(unittest.TestCase):
    def test_signature_matches_dingtalk_algorithm(self):
        timestamp = 1700000000000
        secret = "SEC-test"
        expected = base64.b64encode(
            hmac.new(
                secret.encode(),
                f"{timestamp}\n{secret}".encode(),
                hashlib.sha256,
            ).digest()
        ).decode()
        self.assertEqual(notifier.create_signature(timestamp, secret), expected)

    def test_signed_webhook_keeps_access_token_and_never_contains_secret(self):
        url = notifier.signed_webhook(
            "https://oapi.dingtalk.com/robot/send?access_token=abc",
            "SEC-never-leak",
            1700000000000,
        )
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        self.assertEqual(query["access_token"], "abc")
        self.assertEqual(query["timestamp"], "1700000000000")
        self.assertIn("sign", query)
        self.assertNotIn("SEC-never-leak", url)

    def test_rejects_non_dingtalk_webhook(self):
        with self.assertRaises(notifier.NotificationError):
            notifier.signed_webhook("https://example.com/hook", "secret", 1)

    def test_webhook_diagnostics_do_not_echo_secret_values(self):
        cases = [
            ("", "DINGWEBHOOK is empty"),
            ("DINGWEBHOOK=https://oapi.dingtalk.com/secret", "must not include"),
            ("${{ secrets.DINGWEBHOOK }}", "must not be a GitHub expression"),
            ('"https://oapi.dingtalk.com/secret"', "must not be wrapped in quotes"),
            ("oapi.dingtalk.com/secret", "must start with https://"),
            ("https://example.com/secret", "hostname must be dingtalk.com"),
        ]
        for value, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(notifier.NotificationError) as caught:
                    notifier.signed_webhook(value, "secret", 1)
                self.assertIn(expected, str(caught.exception))
                self.assertNotIn("/secret", str(caught.exception))

    def test_event_payload_is_reminder_only_and_sanitized(self):
        payload = notifier.render_event(
            "submission-valid",
            ASSIGNMENT,
            commit_sha="a" * 40,
            assignment_path="sop/stages/02/dispatch/task.yaml",
            run_url="https://github.example/actions/1",
            detail="token=do-not-print",
        )
        text = payload["markdown"]["text"]
        self.assertEqual(payload["msgtype"], "markdown")
        self.assertIn("不构成 SOP 状态", text)
        self.assertIn("[redacted]", text)
        self.assertNotIn("do-not-print", text)
        self.assertFalse(payload["at"]["isAtAll"])

    def test_task_reminder_targets_only_registered_member(self):
        targets = notifier.load_member_targets(
            json.dumps(
                {
                    "member-a": {
                        "atMobiles": ["13800000000"],
                        "atUserIds": ["manager-001"],
                    }
                }
            ),
            "member-a",
        )
        payload = notifier.render_event(
            "task-reminder",
            ASSIGNMENT,
            commit_sha="b" * 40,
            assignment_path="sop/stages/02/dispatch/task.yaml",
            run_url="https://github.example/actions/3",
            at_mobiles=targets["atMobiles"],
            at_user_ids=targets["atUserIds"],
        )
        self.assertEqual(payload["at"]["atMobiles"], ["13800000000"])
        self.assertEqual(payload["at"]["atUserIds"], ["manager-001"])
        self.assertIn("任务催办提醒", payload["markdown"]["text"])

    def test_member_map_rejects_non_object_target(self):
        with self.assertRaises(notifier.NotificationError):
            notifier.load_member_targets('{"member-a": "13800000000"}', "member-a")

    def test_member_map_rejects_message_injection(self):
        with self.assertRaises(notifier.NotificationError):
            notifier.load_member_targets(
                '{"member-a": {"atMobiles": ["13800000000\\n@all"]}}',
                "member-a",
            )

    def test_send_accepts_success_response(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"errcode": 0, "errmsg": "ok"}
        ).encode()
        with mock.patch.object(notifier.urllib.request, "urlopen", return_value=response) as call:
            notifier.send(
                notifier.render_test("https://github.example/actions/2"),
                webhook="https://oapi.dingtalk.com/robot/send?access_token=abc",
                secret="SEC-test",
                timestamp=1700000000000,
            )
        request = call.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(body["markdown"]["title"], "[SOP 提醒] 钉钉通道测试")


if __name__ == "__main__":
    unittest.main()
