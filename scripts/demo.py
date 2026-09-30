"""End-to-end walkthrough against a running API.

    python scripts/demo.py [--base http://localhost:8000] [--file samples/incident_report.pdf]

Upload -> facts -> generate -> verify -> consistency -> submit -> approve -> export.
Exits non-zero if any step fails, so it doubles as an integration check.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
EDITOR = ("editor@contentbridge.io", "contentbridge")
APPROVER = ("approver@contentbridge.io", "contentbridge")

BOLD, DIM, GREEN, RED, YELLOW, RESET = (
    "\033[1m",
    "\033[2m",
    "\033[32m",
    "\033[31m",
    "\033[33m",
    "\033[0m",
)


def step(n: int, text: str) -> None:
    print(f"\n{BOLD}{n}. {text}{RESET}")


def ok(text: str) -> None:
    print(f"   {GREEN}ok{RESET}  {text}")


def info(text: str) -> None:
    print(f"   {DIM}{text}{RESET}")


def warn(text: str) -> None:
    print(f"   {YELLOW}!{RESET}   {text}")


def die(text: str) -> None:
    print(f"   {RED}fail{RESET} {text}")
    sys.exit(1)


class Client:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.token: str | None = None

    def request(self, method: str, path: str, body=None, raw=False, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(f"{self.base}{path}", data=data, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req) as resp:
                payload = resp.read()
                return payload if raw else (json.loads(payload) if payload else None)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()[:400]
            raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc

    def upload(self, path: pathlib.Path):
        boundary = "----contentbridge-demo"
        body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode()
            + path.read_bytes()
            + f"\r\n--{boundary}--\r\n".encode()
        )
        req = urllib.request.Request(
            f"{self.base}/documents",
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {self.token}",
            },
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def login(self, email: str, password: str):
        self.token = None
        result = self.request("POST", "/auth/login", {"email": email, "password": password})
        self.token = result["access_token"]
        return result["user"]

    def wait(self, job_id: str, label: str, timeout: float = 300.0):
        started = time.time()
        last = ""
        while time.time() - started < timeout:
            job = self.request("GET", f"/jobs/{job_id}")
            if job["stage"] and job["stage"] != last:
                last = job["stage"]
                info(f"{label}: {last}")
            if job["status"] == "succeeded":
                return job
            if job["status"] == "failed":
                die(f"{label} failed: {job['error']}")
            time.sleep(0.4)
        die(f"{label} timed out after {timeout:.0f}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--file", default=str(ROOT / "samples" / "incident_report.pdf"))
    parser.add_argument("--languages", default="en")
    parser.add_argument(
        "--types", default="advisory,summary,ppt", help="comma-separated output types"
    )
    args = parser.parse_args()

    source = pathlib.Path(args.file)
    if not source.exists():
        die(f"{source} not found. Run scripts/make_samples.py first.")

    editor = Client(args.base)
    languages = args.languages.split(",")
    types = args.types.split(",")

    step(1, "Health")
    health = editor.request("GET", "/health")
    if not health["database"]:
        die("database is not reachable")
    ok(f"api up, llm={health['llm_provider']}, embeddings={health['embedding_provider']}")

    step(2, f"Sign in as editor and upload {source.name}")
    user = editor.login(*EDITOR)
    ok(f"{user['email']} ({user['role']})")
    uploaded = editor.upload(source)
    document_id = uploaded["document"]["id"]
    ok(f"document {document_id}")

    step(3, "Intake: parse, index, extract the Source of Truth")
    result = editor.wait(uploaded["job"]["id"], "intake")["result"] or {}
    ok(f"{result.get('blocks')} blocks, {result.get('chunks')} chunks, {result.get('facts')} facts")
    if result.get("note"):
        warn(result["note"])

    sheet = editor.request("GET", f"/documents/{document_id}/fact-sheet")
    cited = sum(1 for f in sheet["facts"] if f["evidence"])
    ok(f"fact sheet v{sheet['version']}: {len(sheet['facts'])} facts, {cited} with evidence")
    if cited != len(sheet["facts"]):
        die("a fact reached the sheet without evidence")

    step(4, "Retrieval check")
    hits = editor.request(
        "GET",
        f"/documents/{document_id}/search?q=how%20many%20credentials%20were%20compromised&limit=1",
    )
    if hits:
        hit = hits[0]
        ok(f"{hit['score']:.3f} -> p{hit['page_no']} {hit['section_path'].split(' > ')[-1]}")

    step(5, f"Generate {len(types)} type(s) x {len(languages)} language(s)")
    job = editor.request(
        "POST",
        f"/documents/{document_id}/outputs",
        {"types": types, "audience": "officer", "languages": languages},
    )
    generated = editor.wait(job["id"], "generation")["result"] or {}
    for failure in generated.get("failures", []):
        warn(failure)
    outputs = editor.request("GET", f"/documents/{document_id}/outputs")
    ok(f"{len(generated.get('outputs', []))} outputs created")

    step(6, "Verify each output")
    for output in outputs:
        job = editor.request("POST", f"/outputs/{output['id']}/verify")
        editor.wait(job["id"], f"verify {output['type']}")
        claims = editor.request("GET", f"/outputs/{output['id']}/claims")
        counts = ", ".join(f"{n} {v}" for v, n in sorted(claims["counts"].items()))
        score = claims["trust_score"]
        ok(f"{output['type']:14} trust {score:.0%}  ({counts})" if score else f"{output['type']}")

    step(7, "Consistency matrix (no model involved)")
    report = editor.request("GET", f"/documents/{document_id}/consistency")
    mismatched = [r for r in report["rows"] if r["has_mismatch"]]
    ok(f"{len(report['rows'])} facts x {len(report['outputs'])} outputs")
    if mismatched:
        for row in mismatched[:5]:
            values = ", ".join(
                f"{c['stated']}{'' if c['agrees'] else ' <-'}" for c in row["cells"] if c["stated"]
            )
            warn(f"{row['key'][:44]}: source {row['expected']} vs {values}")
    else:
        ok("every output agrees with the source")
    if report["unsourced"]:
        for item in report["unsourced"][:3]:
            warn(f"unsourced figure {item['value']}")

    step(8, "Submit for review, then approve as the approver")
    target = outputs[0]
    state = editor.request("GET", f"/outputs/{target['id']}/approval")
    if state["blocking_reasons"]:
        warn(f"{target['type']} is blocked: {'; '.join(state['blocking_reasons'])}")

    editor.request("POST", f"/outputs/{target['id']}/submit", {"note": "Ready for review"})
    ok(f"{target['type']} submitted for review")

    approver = Client(args.base)
    who = approver.login(*APPROVER)
    queue = approver.request("GET", "/review-queue")
    ok(f"{who['email']} sees {len(queue)} item(s) in the queue")

    state = approver.request("GET", f"/outputs/{target['id']}/approval")
    if state["can_approve"]:
        state = approver.request("POST", f"/outputs/{target['id']}/approve", {"note": "Approved"})
        ok(f"approved by {state['approver_name']} at {state['approved_at']}")
    else:
        warn(f"gate held: {'; '.join(state['blocking_reasons']) or 'not approvable'}")
        try:
            approver.request("POST", f"/outputs/{target['id']}/approve", {})
            die("the gate let a blocked output through")
        except RuntimeError as exc:
            ok(f"approval correctly refused ({str(exc).split(':')[-1].strip()[:70]})")

    step(9, "Export")
    exported = 0
    for output in outputs:
        for fmt in output["renderers"]:
            body = editor.request(
                "GET", f"/outputs/{output['id']}/export?format={fmt}&citations=true", raw=True
            )
            exported += 1
            info(f"{output['type']:14} {fmt:9} {len(body):>8,} bytes")
    ok(f"{exported} exports")

    step(10, "Audit trail")
    entries = editor.request("GET", f"/documents/{document_id}/audit")
    for entry in entries[:6]:
        info(f"{entry['created_at'][:19]}  {entry['actor_name'] or '-':16} {entry['action']}")
    ok(f"{len(entries)} entries recorded")

    print(f"\n{GREEN}{BOLD}Demo complete.{RESET} Document {document_id}\n")


if __name__ == "__main__":
    main()
