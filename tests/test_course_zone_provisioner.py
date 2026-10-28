import json
from datetime import date

from src.course_zone_provisioner import CoursePlan, InfraiDnsClient, provision_course_zone


class FakeResponse:
    status = 200

    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def read(self):
        return self.data

    def getheader(self, name, default=None):
        return default


def test_deadline_decision_and_zone_key_are_explicit():
    calls = []

    def opener(request):
        calls.append(request)
        if request.full_url.endswith("/domain/add"):
            return FakeResponse({"ok": True, "data": {"zone_id": "zone-7"}, "error": None, "metadata": {}})
        return FakeResponse({"ok": True, "data": {}, "error": None, "metadata": {}})

    client = InfraiDnsClient("test-key", opener=opener, sleep=lambda _: None)
    report = provision_course_zone(CoursePlan("learn.example.org", date(2024, 1, 1)), client, date(2024, 1, 2))

    assert report.delivery_status == "attention"
    assert [call.method for call in calls] == ["POST", "PUT", "PUT"]
    assert all(json.loads(call.data)["zone_id"] == "zone-7" for call in calls[1:])
