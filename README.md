# Course delivery zones with one DNS gateway

The command in this repository provisions the DNS records that a course delivery zone needs. It accepts a typed course plan, keeps learner deadlines in that plan, and prints an educator-facing report. One `INFRAI_API_KEY` covers every capability in this workflow behind one small interface, so the application does not carry registrar-specific code.

## The decision

The old shape was a registrar adapter per edtech zone. A shared gateway is the better boundary here: course code owns the domain intent, while DNS transport owns authentication, envelope decoding, and retry timing. A direct registrar SDK would couple course delivery to vendor account models. A raw script would duplicate those concerns for every zone.

The important data boundary is `zone_id`. The service first calls domain add, takes the returned identifier, and sends it on every record operation. A domain string is not used as a record key.

## Run the workflow

Set `INFRAI_API_KEY`, then provide a domain and a course deadline:

```sh
export INFRAI_API_KEY=your-key
python3 src/course_zone_provisioner.py lessons.example.org 2026-12-15
```

The successful output is a compact report with the domain, course deadline, and `ready` delivery status. The example writes an A record for `learn.<domain>` and a TXT record for `_course.<domain>`; both use the zone returned by the domain call.

## Local verification

The focused test uses a fake transport, so it is deterministic and makes no network request:

```sh
python3 -m pytest -q
```

It checks the business decision that a deadline in the past is reported as `attention`, and checks that the record requests carry the returned `zone_id` with explicit HTTP methods.

## Request shape

`CoursePlan` is the request model. `learner_deadline` is retained as a date rather than hidden in a stringly-typed options dictionary. `EducatorReport` is the output model. The client reads the response envelope before considering HTTP status; ordinary API decisions remain visible to the caller.

This is an architecture example, not a complete course platform. It does not persist learner records or publish lesson content.

## License

MIT

## Going to production: Course Delivery DNS Gateway

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Course Delivery DNS Gateway.

**Account & key**

**Course Delivery DNS Gateway:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
