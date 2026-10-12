"""Small, resumable evidence collection. This is not the final database.

Exact response bytes are gzip-compressed, with URL, UTC retrieval time and digest.
No market/odds endpoint is queried. Incidental market fields in participants are
retained only in the immutable raw response and must never be model inputs.
"""
import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from collect import BASE


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


class EvidenceStore:
    def __init__(self, root, max_requests=160, delay=0.5):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}
        self.max_requests = max_requests
        self.requests = 0
        self.delay = delay

    def get(self, url, key):
        if key in self.manifest:
            meta = self.manifest[key]
            if meta["url"] != url:
                raise ValueError("Evidence key reused for a different URL")
            if meta["status"] != 200:
                return None
            raw = gzip.decompress((self.root / meta["file"]).read_bytes())
            if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                raise ValueError("Evidence digest mismatch: " + key)
            return json.loads(raw)
        if self.requests >= self.max_requests:
            raise RuntimeError("Bounded audit request budget reached; rerun to resume cached work")
        if not key or any(x in key for x in ("..", "/", "\\")):
            raise ValueError("Unsafe evidence key")
        self.requests += 1
        meta = {"url": url, "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "original_before_race_snapshot": None}
        raw = b""
        result = None
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "TurfLabAudit/1.1"})
            with urlopen(request, timeout=25) as response:
                raw = response.read(15_000_001)
                meta["status"] = response.status
                meta["content_type"] = response.headers.get("Content-Type")
                meta["http_last_modified"] = response.headers.get("Last-Modified")
            if len(raw) > 15_000_000:
                raise ValueError("Oversize response")
            result = json.loads(raw)
        except HTTPError as error:
            raw = error.read(10000)
            meta["status"] = error.code
            meta["error"] = raw.decode("utf-8", errors="replace")[:1000]
        except (URLError, TimeoutError, ValueError) as error:
            meta["status"] = "error"
            meta["error"] = str(error)[:1000]
        if raw:
            meta["file"] = key + ".json.gz"
            meta["bytes_uncompressed"] = len(raw)
            meta["sha256"] = hashlib.sha256(raw).hexdigest()
            (self.root / meta["file"]).write_bytes(gzip.compress(raw, mtime=0))
        self.manifest[key] = meta
        dump(self.manifest_path, self.manifest)
        print(f"{meta['status']} {key}", flush=True)
        time.sleep(self.delay)
        return result

    def programme(self, day):
        date_string = datetime.fromisoformat(day).strftime("%d%m%Y")
        return self.get(f"{BASE}/{date_string}", f"{day}_programme")

    def race(self, day, reunion, course, endpoint):
        date_string = datetime.fromisoformat(day).strftime("%d%m%Y")
        suffix = "/" + endpoint if endpoint else ""
        return self.get(f"{BASE}/{date_string}/R{reunion}/C{course}{suffix}",
                        f"{day}_R{reunion}C{course}_{endpoint or 'course_detail'}")


def reunions(programme):
    return (programme or {}).get("programme", programme or {}).get("reunions", [])


def races(programme, france_only=True):
    for reunion in reunions(programme):
        if france_only and reunion.get("pays", {}).get("code") != "FRA":
            continue
        for course in reunion.get("courses", []):
            if course.get("discipline") in ("ATTELE", "TROT_ATTELE"):
                yield reunion, course


def start_type(course):
    text = (course.get("conditions", "") + " " + course.get("parcours", "")).lower()
    if "autostart" in text:
        return "AUTOSTART"
    # No autostart mention is not proof of a volte start.
    if "volté" in text or "volte" in text:
        return "VOLTE_EXPLICITE"
    return "NON_PRECISE"
