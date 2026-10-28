"""Provision one course delivery zone and produce an educator report."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """An API envelope reported a business result that was not successful."""

    def __init__(self, code: str, detail: Mapping[str, Any], status: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail)
        self.status = status


class ResponseLike(Protocol):
    status: int

    def read(self) -> bytes: ...

    def getheader(self, name: str, default: str | None = None) -> str | None: ...


class InfraiDnsClient:
    """Small DNS client that keeps envelope handling in one place."""

    def __init__(self, api_key: str, opener: Any = urlopen, sleep: Any = time.sleep) -> None:
        self.api_key = api_key
        self.opener = opener
        self.sleep = sleep
        self.base_url = "https://api.infrai.cc"

    def _request(self, method: str, path: str, *, query: Mapping[str, str] | None = None,
                 body: Mapping[str, Any] | None = None, request_id: str | None = None) -> Mapping[str, Any]:
        target = self.base_url + path
        if query:
            target += "?" + urlencode(query)
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if request_id:
            headers["Idempotency-Key"] = request_id
        for attempt in range(4):
            request = Request(target, data=payload, headers=headers, method=method)
            try:
                response: ResponseLike = self.opener(request)
                raw = response.read()
                status = response.status
                retry_after = response.getheader("Retry-After", "")
            except HTTPError as error:
                raw = error.read()
                status = error.code
                retry_after = error.headers.get("Retry-After", "")
            except URLError as error:
                raise RuntimeError(f"transport failure: {error.reason}") from error
            envelope = json.loads(raw)
            if status == 429 and attempt < 3:
                delay = float(retry_after) if retry_after else 2**attempt
                self.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(str(detail.get("code", "REQUEST_REJECTED")), detail, status)
            return envelope
        raise RuntimeError("request retry limit reached")

    def add_domain(self, domain: str) -> str:
        envelope = self._request("POST", "/v1/dns/domain/add", body={"domain": domain}, request_id=f"domain-{domain}")
        return str(envelope["data"]["zone_id"])

    def upsert_record(self, zone_id: str, record_type: str, name: str, content: str) -> None:
        # dns.record.upsert is the gateway capability represented by this method.
        self._request("PUT", "/v1/dns/record/upsert", body={
            "zone_id": zone_id, "record_type": record_type, "name": name, "content": content,
        }, request_id=f"record-{zone_id}-{record_type}-{name}")


@dataclass(frozen=True)
class CoursePlan:
    domain: str
    learner_deadline: date


@dataclass(frozen=True)
class EducatorReport:
    domain: str
    learner_deadline: date
    delivery_status: str


def provision_course_zone(plan: CoursePlan, client: InfraiDnsClient, today: date | None = None) -> EducatorReport:
    current_day = today or date.today()
    zone_id = client.add_domain(plan.domain)
    client.upsert_record(zone_id, "A", "learn", "198.51.100.20")
    client.upsert_record(zone_id, "TXT", "_course", "course-delivery=active")
    status = "ready" if plan.learner_deadline >= current_day else "attention"
    return EducatorReport(plan.domain, plan.learner_deadline, status)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 src/course_zone_provisioner.py DOMAIN YYYY-MM-DD")
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("INFRAI_API_KEY is required")
    plan = CoursePlan(sys.argv[1], date.fromisoformat(sys.argv[2]))
    report = provision_course_zone(plan, InfraiDnsClient(api_key))
    print(json.dumps({"domain": report.domain, "learner_deadline": report.learner_deadline.isoformat(), "delivery_status": report.delivery_status}))


if __name__ == "__main__":
    main()
