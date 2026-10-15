"""Durable history on a separate GitHub branch, with optimistic concurrency.

An upload intent MUST be persisted before sending video bytes. Ambiguous uploads
are deliberately blocked instead of uploading again after a runner crash.
"""
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .common import ROOT, retry, write_json


class StateError(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


class History:
    branch = "factory-state"
    file = "history.json"

    def __init__(self, local_path=None):
        self.local_path = Path(local_path or ROOT / ".factory/history.json")
        self.remote = bool(os.getenv("GITHUB_ACTIONS") == "true")
        self.repo = os.getenv("GITHUB_REPOSITORY", "")
        self.token = os.getenv("GH_STATE_TOKEN", "")
        self.sha = None
        self.data = {"version": 1, "entries": {}}

    def api(self, method, endpoint, payload=None):
        if not self.repo or not self.token:
            raise StateError("GitHub history credentials are unavailable")
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo}/{endpoint}",
            data=body, method=method,
            headers={"Authorization": f"Bearer {self.token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json"})
        def call():
            with urllib.request.urlopen(request, timeout=40) as response:
                return json.load(response)
        return retry(call, retryable=lambda e: isinstance(e, (TimeoutError, OSError))
                     and (not isinstance(e, urllib.error.HTTPError) or e.code >= 500))

    def load(self):
        if not self.remote:
            if self.local_path.exists():
                self.data = json.loads(self.local_path.read_text(encoding="utf-8"))
            self.validate()
            return self
        try:
            result = self.api("GET", f"contents/{self.file}?ref={self.branch}")
            self.sha = result["sha"]
            self.data = json.loads(base64.b64decode(result["content"]))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise StateError("Cannot read persistent history") from None
            # Create only when the branch is actually absent; never reset an existing branch.
            try:
                self.api("GET", f"git/ref/heads/{self.branch}")
            except urllib.error.HTTPError as missing:
                if missing.code != 404:
                    raise StateError("Cannot inspect history branch") from None
                default = self.api("GET", "")["default_branch"]
                head = self.api("GET", f"git/ref/heads/{default}")["object"]["sha"]
                self.api("POST", "git/refs", {"ref": f"refs/heads/{self.branch}", "sha": head})
                self.save()
            else:
                raise StateError("History file missing on existing branch; refusing to reset it")
        self.validate()
        return self

    def validate(self):
        if not isinstance(self.data, dict) or self.data.get("version") != 1 or not isinstance(self.data.get("entries"), dict):
            raise StateError("Invalid history; refusing to ignore it")
        if any(not isinstance(entry, dict) or entry.get("status") not in
               {"rendered", "uploading", "uncertain", "uploaded", "abandoned"}
               for entry in self.data["entries"].values()):
            raise StateError("Invalid history entry; upload is blocked")

    def save(self):
        if not self.remote:
            write_json(self.local_path, self.data)
            return
        payload = {"message": "Record Shorts factory checkpoint [skip ci]",
                   "branch": self.branch,
                   "content": base64.b64encode(json.dumps(self.data, ensure_ascii=False).encode()).decode()}
        if self.sha:
            payload["sha"] = self.sha
        try:
            result = self.api("PUT", f"contents/{self.file}", payload)
            self.sha = result["content"]["sha"]
        except Exception:
            # A lost response may have committed the write. Reconcile by reading, never overwrite.
            try:
                current = self.api("GET", f"contents/{self.file}?ref={self.branch}")
                if json.loads(base64.b64decode(current["content"])) == self.data:
                    self.sha = current["sha"]
                    return
            except Exception:
                pass
            raise StateError("History checkpoint failed; upload is blocked") from None

    def mark(self, key, status, **fields):
        entry = self.data["entries"].setdefault(key, {})
        entry.update(status=status, updated_at=now(), **fields)
        self.save()

    def ambiguous(self):
        return [key for key, entry in self.data["entries"].items()
                if entry.get("status") in {"uploading", "uncertain"}]
